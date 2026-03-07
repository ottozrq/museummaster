"""Configuration setup for pytest - museummaster backend tests

This conftest.py provides fixtures similar to gagaou but adapted for museummaster's
API-only architecture (no database, just analyze and tts endpoints).
"""

import os
import uuid
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Optional

import jwt
import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ.setdefault("MUSEUMFLAGS_FILE", "flags.yml")
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["OPENAI_MUSEUM_MODEL"] = "gpt-4o"
os.environ["OPENAI_TTS_MODEL"] = "gpt-4o-mini-tts"
os.environ["OPENAI_TTS_VOICE"] = "alloy"


class FakeOpenAI:
    """Mock OpenAI client for testing"""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.responses = SimpleNamespace(create=self._create_response)
        self.audio = SimpleNamespace(speech=SimpleNamespace(create=self._create_speech))

    def _create_response(self, **_: object) -> object:
        return SimpleNamespace(output_text="Mocked analyze output")

    def _create_speech(self, **_: object) -> object:
        return SimpleNamespace(read=lambda: b"fake-mp3-bytes")


# Import app after setting environment variables
from app import get_app


@pytest.fixture(scope="session")
def test_app():
    """Create test FastAPI application"""
    return get_app()


@pytest.fixture
def client(test_app) -> TestClient:
    """Create test client - similar to gagaou's api_client fixture"""
    return TestClient(test_app, base_url="http://127.0.0.1")


# ============================================
# Authentication Fixtures (similar to gagaou)
# ============================================


@pytest.fixture
def test_secret():
    """Get the login secret for JWT token generation"""
    from utils import flags

    return flags.MuseumFlags.get().login_secret


@pytest.fixture
def user_admin(test_secret):
    """Create admin user token - similar to gagaou's user_admin fixture"""
    token = jwt.encode(
        {"user_id": str(uuid.uuid4()), "role": "admin"}, test_secret, algorithm="HS256"
    )
    return {
        "user_id": uuid.UUID(
            jwt.decode(token, test_secret, algorithms=["HS256"])["user_id"]
        ),
        "role": "admin",
        "token": token,
        "email": "admin@example.com",
    }


@pytest.fixture
def user_client_user(test_secret):
    """Create regular client user token"""
    token = jwt.encode(
        {"user_id": str(uuid.uuid4()), "role": "client"}, test_secret, algorithm="HS256"
    )
    return {
        "user_id": uuid.UUID(
            jwt.decode(token, test_secret, algorithms=["HS256"])["user_id"]
        ),
        "role": "client",
        "token": token,
        "email": "user@example.com",
    }


@pytest.fixture
def auth_headers_admin(user_admin):
    """Get authorization headers for admin user"""
    return {"Authorization": f"Bearer {user_admin['token']}"}


@pytest.fixture
def auth_headers_client(user_client_user):
    """Get authorization headers for regular user"""
    return {"Authorization": f"Bearer {user_client_user['token']}"}


# ============================================
# OpenAI Mock Fixtures
# ============================================


@pytest.fixture
def mock_openai_success(monkeypatch):
    """Mock successful OpenAI responses - similar to existing fixture"""
    from routers import analyze, tts

    monkeypatch.setattr(analyze, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(tts, "OpenAI", FakeOpenAI)


@pytest.fixture
def mock_openai_failure(monkeypatch):
    """Mock OpenAI failure for error testing"""

    class FailedOpenAI:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key
            self.responses = SimpleNamespace(create=self._fail_response)
            self.audio = SimpleNamespace(
                speech=SimpleNamespace(create=self._fail_speech)
            )

        def _fail_response(self, **_: object) -> object:
            raise Exception("OpenAI API error")

        def _fail_speech(self, **_: object) -> object:
            raise Exception("OpenAI TTS error")

    from routers import analyze, tts

    monkeypatch.setattr(analyze, "OpenAI", FailedOpenAI)
    monkeypatch.setattr(tts, "OpenAI", FailedOpenAI)


# ============================================
# API Client Wrapper (similar to gagaou)
# ============================================


@dataclass
class ApiClient:
    """Wrapper around TestClient providing convenient methods - similar to gagaou's ApiClient"""

    client: TestClient
    user: Optional[dict] = None

    def get(self, url: str, **kwargs):
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self._request("POST", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self._request("DELETE", url, **kwargs)

    def patch(self, url: str, **kwargs):
        return self._request("PATCH", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs):
        headers = kwargs.pop("headers", {})
        if self.user:
            headers.setdefault("Authorization", f"Bearer {self.user['token']}")

        response = self.client.request(
            method=method, url=url, headers=headers, **kwargs
        )
        return response


@pytest.fixture
def api_client(client) -> ApiClient:
    """Create API client wrapper - similar to gagaou's api_client fixture"""
    return ApiClient(client=client)


@pytest.fixture
def api_client_auth(client, user_admin) -> ApiClient:
    """Create authenticated API client - similar to gagaou's api_client fixture"""
    return ApiClient(client=client, user=user_admin)


# ============================================
# Test Data Fixtures
# ============================================


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes for testing"""
    return b"fake-png-image-bytes"


@pytest.fixture
def sample_text():
    """Create sample text for TTS testing"""
    return "Hello, welcome to the museum."


@pytest.fixture
def long_text():
    """Create longer text for TTS testing"""
    return "This is a longer text that can be used for testing TTS. " * 10


# ============================================
# Query Counter (from gagaou)
# ============================================


class QueryCounter:
    """
    Counter for tracking API queries.
    Usage:
        query_counter.query_count = 0
        # ... make API call ...
        assert query_counter.query_count <= expected
    """

    def __init__(self):
        self.query_count = 0

    def count(self):
        self.query_count += 1

    def reset(self):
        self.query_count = 0


query_counter = QueryCounter()


@pytest.fixture
def _query_counter():
    """Reset query counter before each test"""
    query_counter.reset()
    yield query_counter
    query_counter.reset()
