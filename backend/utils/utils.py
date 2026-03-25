import logging
import numbers
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Generator, Iterator

import casbin
import jinja2
import psycopg2.extras
from postgis.psycopg import register
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import Session, session, sessionmaker

from utils import flags

MF = flags.MuseumFlags.get()


@dataclass(frozen=True)
class SessionMaker:
    engine: Engine
    SessionLocal: sessionmaker

    def make_session(self) -> Session:
        return self.SessionLocal()

    @classmethod
    def make(cls, engine: Engine) -> "SessionMaker":
        return cls(engine, sessionmaker(autocommit=False, autoflush=False, bind=engine))


env = jinja2.Environment(loader=jinja2.FileSystemLoader("."))
env.filters["ix"] = lambda a, b: set(a) & set(b)
env.filters["diffx"] = lambda a, b: set(a) - set(b)


def escape_sql(st):
    return st.replace("'", "\\'")


def sql_litteral(lit):
    if isinstance(lit, str):
        return f"'{escape_sql(lit)}'"
    elif isinstance(lit, numbers.Number):
        return str(lit)
    elif isinstance(lit, bool):
        return str(lit)
    elif lit is None:
        return "NULL"
    elif isinstance(lit, datetime):
        return f"'{lit}'::TIMESTAMP"
    elif isinstance(lit, list):
        return ",".join([sql_litteral(v) for v in lit])
    elif isinstance(lit, tuple):
        return ",".join([sql_litteral(v) for v in lit])
    elif isinstance(lit, Generator):
        return ",".join([sql_litteral(v) for v in lit])
    else:
        raise Exception(str(type(lit)))


def inject_params(sql_tpl: str, params) -> str:
    result = sql_tpl
    # sorting in reverse order ensure that we try to replace :key_extented before :key
    for key in sorted(params, reverse=True):
        result = result.replace(f":{key}", sql_litteral(params[key]))
    return result


@dataclass(frozen=True)
class MuseumDb:
    session: session.Session
    engine: Engine

    def scalar(self, *args, **kwargs):
        return next(self(*args, **kwargs))[0]

    def __call__(self, *args, **kwargs):
        return self.run_sql(*args, **kwargs)

    def _sql(self, sql: str, jinja_params=None):
        if isinstance(sql, Path):
            return sql.read_text()
        sql = str(sql)
        if len(str(sql)) > 220:
            return sql
        if jinja_params:
            return env.get_template(sql).render(jinja_params)
        path = Path(sql)
        if not path.is_file():
            return sql
        text = path.read_text()
        return text

    def run_sql(self, sql, params=None, jinja_params=None):
        expanded_query = self._sql(sql, jinja_params)
        if flags.SqlAlchemyFlags().echo:
            if params:
                logging.info(inject_params(expanded_query, params))
            else:
                logging.info(expanded_query)

        return self.session.execute(expanded_query, params)

    # function to only return the sql string, without executing it
    def get_sql(self, sql, params=None, jinja_params=None):
        expanded_query = self._sql(sql, jinja_params)

        if params:
            return inject_params(expanded_query, params)

        return expanded_query


@dataclass
class SingletonDatabaseConnection:

    def make_session(self) -> Session:
        return Session(bind=self._engine)

    @cached_property
    def _engine(self) -> Engine:
        raise NotImplementedError()

    @cached_property
    def session_maker(self) -> SessionMaker:
        return SessionMaker.make(self._engine)

    @property
    def new_session(self) -> Session:
        return self.session_maker.SessionLocal()

    def new_session_with_engine(self, engine: Engine) -> Session:
        return SessionMaker.make(engine).SessionLocal()

    @contextmanager
    def museum_db(self, engine: Engine = None) -> Iterator[MuseumDb]:
        if engine:
            new_session = self.new_session_with_engine(engine)
        else:
            new_session = self.new_session
            engine = self._engine
        with closing(new_session) as session:
            yield MuseumDb(self.prepped_session(session), engine)

    def prepped_session(self, session: Session) -> Session:
        return session


@dataclass
class _Connection(SingletonDatabaseConnection):
    url: str = None
    flags = None
    pool_size: int = 5
    max_overflow: int = 10

    @cached_property
    def _engine(self) -> Engine:
        return create_engine(
            (self.flags and self.flags.get().url)
            or self.url
            or flags.PostgresqlFlags.get().url,
            execution_options={
                "schema_translate_map": {"museum_sources": "museum_sources"}
            },
            echo=flags.SqlAlchemyFlags.get().echo,
            connect_args={
                "options": "-c timezone=utc",
                "cursor_factory": psycopg2.extras.NamedTupleCursor,
                **(
                    ({} if not self.flags.get().ssl_mode else {"sslmode": "require"})
                    if self.flags
                    else (
                        {}
                        if not flags.PostgresqlFlags.get().ssl_mode
                        else {"sslmode": "require"}
                    )
                ),
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
            executemany_mode="values",
            # https://docs.sqlalchemy.org/en/14/core/pooling.html
            # https://stackoverflow.com/questions/58866560/flask-sqlalchemy-pool-pre-ping-only-working-sometimes  # noqa
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
        )

    def prepped_session(self, session: Session) -> Session:
        # postgis 在某些环境可能未安装或与 PostgreSQL 版本不兼容。
        # 对大多数非 GIS 单测/场景应当允许降级运行。
        try:
            register(session.bind.raw_connection())
        except Exception:
            pass
        return super(_Connection, self).prepped_session(session)


_connection = _Connection()


def get_postgres_sessionmaker(
    url: str = None,
    reset_cache: bool = False,
    flags=None,
    pool_size: int = 5,
    max_overflow: int = 10,
) -> SessionMaker:
    if url:
        _connection.url = url
    if flags:
        _connection.flags = flags
    if pool_size:
        _connection.pool_size = pool_size
    if max_overflow:
        _connection.max_overflow = max_overflow
    if reset_cache:
        if hasattr(_connection, "_engine"):
            del _connection._engine
        if hasattr(_connection, "session_maker"):
            del _connection.session_maker
    return _connection.session_maker


@contextmanager
def postgres_session() -> Iterator[MuseumDb]:
    with _connection.museum_db() as museum_db:
        yield museum_db


def make_session() -> Session:
    return _connection.make_session()


class MuseumEnforcer:
    def __init__(self) -> None:
        self.enforcer = casbin.Enforcer(
            str(Path(__file__).parent / "rbac/model.conf"),
            str(Path(__file__).parent / "rbac/policy.csv"),
        )
        self.enforcer.logger.error = self.enforcer.logger.info

    def enforce(self, role, path, method):
        return self.enforcer.enforce(role, path, method)


enforcer = MuseumEnforcer()
