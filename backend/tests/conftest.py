"""Configuration setup for pytest"""

from types import SimpleNamespace

import postgis
import pytest
import sqlalchemy
import testing.postgresql
from fastapi import testclient
from passlib.context import CryptContext
from sqlalchemy.orm import scoped_session

import depends as d
import sql_models as sm
from app import get_app
from tests import fixtures as fixts
from tests import utils
from utils.utils import MuseumDb

from .sqlalchemy_fixture_factory.sqla_fix_fact import SqlaFixFact

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Raw TestClient and OpenAI/API mocks (for analyze, tts, auth tests)
# ---------------------------------------------------------------------------


class _FakeStreamingResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def iter_bytes(self):
        return iter([b"fake-mp3-bytes"])


class FakeOpenAI:
    """Mock OpenAI client for analyze and TTS tests."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.responses = SimpleNamespace(create=self._create_response)
        self.audio = SimpleNamespace(
            speech=SimpleNamespace(
                create=self._create_speech,
                with_streaming_response=SimpleNamespace(
                    create=lambda **kw: _FakeStreamingResponse()
                ),
            )
        )

    def _create_response(self, **kw):
        return SimpleNamespace(output_text="Mocked analyze output")

    def _create_speech(self, **kw):
        return SimpleNamespace(read=lambda: b"fake-mp3-bytes")


class FakeAsyncOpenAI(FakeOpenAI):
    """Async OpenAI mock; same as FakeOpenAI for create, stream uses sync-style."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def client(app):
    """Raw TestClient for endpoints that need file upload or no auth (e.g. analyze, tts, auth)."""
    return testclient.TestClient(app, base_url="http://127.0.0.1")


@pytest.fixture
def mock_openai_success(monkeypatch):
    """Mock OpenAI and AsyncOpenAI so analyze and tts succeed without real API key."""
    from src.routes import analyze, tts

    monkeypatch.setattr(analyze, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(analyze, "AsyncOpenAI", FakeAsyncOpenAI)
    monkeypatch.setattr(tts, "OpenAI", FakeOpenAI)


@pytest.fixture
def mock_openai_failure(monkeypatch):
    """Mock OpenAI to raise so we can test 500 handling."""

    def _raise(*a, **k):
        raise Exception("OpenAI error")

    class FailedOpenAI:
        def __init__(self, api_key: str = ""):
            self.responses = SimpleNamespace(create=_raise)
            self.audio = SimpleNamespace(
                speech=SimpleNamespace(create=_raise),
                with_streaming_response=SimpleNamespace(create=_raise),
            )

    from src.routes import analyze, tts

    monkeypatch.setattr(analyze, "OpenAI", FailedOpenAI)
    monkeypatch.setattr(analyze, "AsyncOpenAI", FailedOpenAI)
    monkeypatch.setattr(tts, "OpenAI", FailedOpenAI)


@pytest.fixture
def sample_image_bytes():
    return b"fake-png-image-bytes"


@pytest.fixture
def sample_text():
    return "Hello, welcome to the museum."


@pytest.fixture
def test_secret():
    from utils import flags
    return flags.MuseumFlags.get().login_secret


@pytest.fixture(scope="session")
def app():
    with testing.postgresql.Postgresql() as p:
        app = get_app(url=p.url(), pool_size=20, max_overflow=50)
        session = app.postgres_sessionmaker.SessionLocal()

        for extension in (
            "postgis",
            "uuid-ossp",
        ):
            session.execute(f'create extension if not exists "{extension}";')
        for schema in {
            schema
            for schema, _ in (
                table.split(".", 1) for table in sm.PsqlBase.metadata.tables
            )
        }:
            session.execute(f'create schema if not exists "{schema}";')
        session.commit()
        sm.PsqlBase.metadata.create_all(session.bind)
        session.close()
        yield app


class QueryCounter:
    """
    Example usage:
    In your unit test :

    # Initialize the query counter
    query_counter.query_count = 0

    # Make the call/action that you want to count the queries for
    reports = reports_m.ReportCollection.from_response(cl(zone_model.reports))

    # Assert that the number of queries is what you expect
    assert query_counter.query_count <= 10
    """

    def __init__(self):
        self.query_count = 0

    def count_queries(self, conn, cursor, statement, parameters, context, executemany):
        # Remove the following line if you want to see the queries while running tests
        # It help understands why so many queries are run sometimes
        # print(statement)
        self.query_count += 1


query_counter = QueryCounter()


@pytest.fixture
def _api_client(app, monkeypatch, mocker):
    # Start a transaction
    connection = app.postgres_sessionmaker.engine.connect()
    transaction = connection.begin()

    session = scoped_session(
        app.postgres_sessionmaker.SessionLocal, scopefunc=lambda: ""
    )
    postgis.psycopg.register(session.bind.raw_connection())
    connection.force_close = connection.close
    transaction.force_rollback = transaction.rollback

    connection.close = lambda: None
    transaction.rollback = lambda: None
    session.close = lambda: None
    # Begin a nested transaction (any new transactions created in the codebase
    # will be held until this outer transaction is committed or closed)
    session.begin_nested()

    # Each time the SAVEPOINT for the nested transaction ends, reopen it
    @sqlalchemy.event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, trans):
        if trans.nested and not trans._parent.nested:
            # ensure that state is expired the way
            # session.commit() at the top level normally does
            session.expire_all()

            session.begin_nested()

    # Force the connection to use nested transactions
    connection.begin = connection.begin_nested

    # If an object gets moved to the 'detached' state by a call to flush the session,
    # add it back into the session (this allows us to see changes made to objects
    # in the context of a test, even when the change was made elsewhere in
    # the codebase)
    @sqlalchemy.event.listens_for(session, "persistent_to_detached")
    @sqlalchemy.event.listens_for(session, "deleted_to_detached")
    def rehydrate_object(session, obj):
        session.add(obj)

    @sqlalchemy.event.listens_for(
        app.postgres_sessionmaker.engine, "before_cursor_execute"
    )
    def receive_before_cursor_execute(
        conn, cursor, statement, params, context, executemany
    ):
        query_counter.count_queries(
            conn, cursor, statement, params, context, executemany
        )
        return statement, params

    try:
        fix = SqlaFixFact(session)

        def override_get_db():
            session.begin_nested()
            yield MuseumDb(session, app.postgres_sessionmaker.engine)
            session.commit()
            session.close()

        app.dependency_overrides[d.get_psql] = override_get_db
        mocks = utils.Mocks.make(mocker)
        yield utils.ApiClient(
            db=MuseumDb(session, app.postgres_sessionmaker.engine),
            app=app,
            # base_url is added to get around le-village WIFI problem.
            client=testclient.TestClient(app, base_url="http://127.0.0.1"),
            fix=fix,
            session=session,
            mocks=mocks,
            user=None,
            default_user=None,
        )
    finally:
        session.expire_all()
        session.remove()
        transaction.force_rollback()
        connection.force_close()
        assert not session.query(sm.User).count()
        sqlalchemy.event.remove(
            app.postgres_sessionmaker.engine,
            "before_cursor_execute",
            receive_before_cursor_execute,
        )


@pytest.fixture
def fix(_api_client: utils.ApiClient):
    return _api_client.fix


@pytest.fixture
def cl(api_client) -> utils.ApiClient:
    return api_client


@pytest.fixture
def api_client(_api_client: utils.ApiClient, user_admin) -> utils.ApiClient:
    _api_client.user = user_admin
    _api_client.default_user = _api_client.user
    _api_client.login(user_admin, superuser=True)
    yield _api_client


@pytest.fixture
def user_admin(fix):
    return fixts.User(
        fix,
        user_email="otto@ottozhang.com",
        password=pwd_context.hash("666666"),
        user_id="00000000-0000-0000-0000-000000000001",
        role=sm.UserRole.admin,
    ).create()


@pytest.fixture
def user_editor(fix):
    return fixts.User(
        fix,
        user_email="editor@ottozhang.com",
        password=pwd_context.hash("666666"),
        user_id="00000000-0000-0000-0000-000000000002",
        role=sm.UserRole.editor,
        extras={},
    ).create()
