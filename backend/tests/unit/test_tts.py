"""Unit tests for TTS endpoint - similar to gagaou's test pattern

Tests cover:
- Basic TTS functionality
- Authentication requirements
- Error handling
- Request validation
- Response formats
- Text length handling
"""

import base64

from fastapi.testclient import TestClient

from tests.conftest import ApiClient
from utils.flags import OpenAIFlags


class TestTTSEndpoint:
    """Tests for /tts endpoint - similar to gagaou's test structure"""

    def test_tts_with_valid_text(
        self, client: TestClient, mock_openai_success, sample_text
    ):
        """Test TTS endpoint with valid text - basic CRUD: READ"""
        response = client.post("/tts", json={"text": sample_text})

        assert response.status_code == 200
        data = response.json()
        assert "audio_base64" in data
        assert "mime_type" in data
        assert "voice" in data
        assert data["mime_type"] == "audio/mpeg"
        assert data["voice"] == "alloy"

    def test_tts_returns_valid_audio(
        self, client: TestClient, mock_openai_success, sample_text
    ):
        """Test TTS endpoint returns valid audio data"""
        response = client.post("/tts", json={"text": sample_text})

        data = response.json()
        # Verify audio can be decoded from base64
        audio_bytes = base64.b64decode(data["audio_base64"])
        assert audio_bytes == b"fake-mp3-bytes"

    def test_tts_with_empty_text(self, client: TestClient):
        """Test TTS endpoint rejects empty text"""
        response = client.post("/tts", json={"text": ""})

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_tts_with_whitespace_only(self, client: TestClient):
        """Test TTS endpoint rejects whitespace-only text"""
        response = client.post("/tts", json={"text": "   "})

        assert response.status_code == 400

    def test_tts_with_missing_text(self, client: TestClient):
        """Test TTS endpoint requires text field"""
        response = client.post("/tts", json={})

        assert response.status_code == 422  # FastAPI validation error

    def test_tts_with_long_text(
        self, client: TestClient, mock_openai_success, long_text
    ):
        """Test TTS endpoint handles long text"""
        response = client.post("/tts", json={"text": long_text})

        assert response.status_code == 200
        data = response.json()
        assert "audio_base64" in data

    def test_tts_with_special_characters(self, client: TestClient, mock_openai_success):
        """Test TTS endpoint handles special characters"""
        special_text = "Hello! 你好🎨 #museum @artwork 'quotes' \"double quotes\""
        response = client.post("/tts", json={"text": special_text})

        assert response.status_code == 200

    def test_tts_with_multilingual_text(self, client: TestClient, mock_openai_success):
        """Test TTS endpoint handles multilingual text"""
        multilingual_text = "Hello! Bonjour! 你好! こんにちは! مرحبا!"
        response = client.post("/tts", json={"text": multilingual_text})

        assert response.status_code == 200

    def test_tts_with_openai_failure(
        self, client: TestClient, mock_openai_failure, sample_text
    ):
        """Test TTS endpoint handles OpenAI failures gracefully"""
        response = client.post("/tts", json={"text": sample_text})

        assert response.status_code == 500
        assert "detail" in response.json()

    def test_tts_missing_api_key(self, client: TestClient, monkeypatch, sample_text):
        """Test TTS endpoint requires API key"""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setattr(
            OpenAIFlags, "_default", None
        )  # force next get() to read env
        response = client.post("/tts", json={"text": sample_text})

        assert response.status_code == 500
        assert "API_KEY" in response.json()["detail"]

    def test_tts_response_format(self, client: TestClient, mock_openai_success):
        """Test TTS endpoint returns correct response format"""
        response = client.post("/tts", json={"text": "Hello"})

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        required_fields = ["audio_base64", "mime_type", "voice"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_tts_response_mime_type(self, client: TestClient, mock_openai_success):
        """Test TTS endpoint returns correct MIME type"""
        response = client.post("/tts", json={"text": "Test"})

        data = response.json()
        assert data["mime_type"] == "audio/mpeg"

    def test_tts_response_voice(self, client: TestClient, mock_openai_success):
        """Test TTS endpoint returns correct voice"""
        response = client.post("/tts", json={"text": "Test"})

        data = response.json()
        assert data["voice"] == "alloy"


class TestTTSWithAuth:
    """Tests for TTS endpoint with authentication - similar to gagaou's auth tests"""

    def test_tts_works_without_auth(
        self, client: TestClient, mock_openai_success, sample_text
    ):
        """Test TTS endpoint works without authentication"""
        response = client.post("/tts", json={"text": sample_text})

        assert response.status_code == 200

    def test_tts_with_admin_auth(
        self, client: TestClient, mock_openai_success, sample_text, auth_headers_admin
    ):
        """Test TTS endpoint works with admin authentication"""
        response = client.post(
            "/tts", json={"text": sample_text}, headers=auth_headers_admin
        )

        assert response.status_code == 200

    def test_tts_with_client_auth(
        self, client: TestClient, mock_openai_success, sample_text, auth_headers_client
    ):
        """Test TTS endpoint works with regular user authentication"""
        response = client.post(
            "/tts", json={"text": sample_text}, headers=auth_headers_client
        )

        assert response.status_code == 200


class TestTTSApiClient:
    """Tests using the ApiClient wrapper - following gagaou's pattern"""

    def test_post_using_api_client(
        self, api_client: ApiClient, mock_openai_success, sample_text
    ):
        """Test using ApiClient wrapper for POST requests"""
        response = api_client.post("/tts", json={"text": sample_text})

        assert response.status_code == 200
        data = response.json()
        assert data["audio_base64"] == base64.b64encode(b"fake-mp3-bytes").decode(
            "utf-8"
        )

    def test_authenticated_request_using_api_client(
        self, api_client_auth: ApiClient, mock_openai_success, sample_text
    ):
        """Test using authenticated ApiClient wrapper"""
        response = api_client_auth.post("/tts", json={"text": sample_text})

        assert response.status_code == 200
        data = response.json()
        assert "audio_base64" in data


class TestTTSPagination:
    """Tests for TTS pagination/filtering - similar to gagaou's pattern"""

    def test_tts_multiple_requests(
        self, client: TestClient, mock_openai_success, sample_text
    ):
        """Test multiple TTS requests work independently"""
        # Make multiple requests
        response1 = client.post("/tts", json={"text": sample_text})
        response2 = client.post("/tts", json={"text": "Different text"})

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Both should return valid audio
        assert "audio_base64" in response1.json()
        assert "audio_base64" in response2.json()
