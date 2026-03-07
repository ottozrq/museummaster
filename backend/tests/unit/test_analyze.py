"""Unit tests for analyze endpoint - similar to gagaou's test pattern

Tests cover:
- Basic analyze functionality
- Authentication requirements
- Error handling
- Request validation
- Response formats
"""

from fastapi.testclient import TestClient

from tests.conftest import ApiClient
from utils.flags import OpenAIFlags


class TestAnalyzeEndpoint:
    """Tests for /analyze endpoint - similar to gagaou's test structure"""

    def test_health_check(self, client: TestClient):
        """Test basic health check - verify API is working"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "museum-guide-backend"}

    def test_analyze_with_valid_image(
        self, client: TestClient, mock_openai_success, sample_image_bytes
    ):
        """Test analyze endpoint with valid image - basic CRUD: READ"""
        # Create fake image file
        files = {"image": ("art.png", sample_image_bytes, "image/png")}
        response = client.post("/analyze", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert data["text"] == "Mocked analyze output"

    def test_analyze_with_different_image_formats(
        self, client: TestClient, mock_openai_success
    ):
        """Test analyze endpoint with different image formats"""
        # Test JPEG
        files = {"image": ("art.jpg", b"fake-jpeg", "image/jpeg")}
        response = client.post("/analyze", files=files)
        assert response.status_code == 200

        # Test PNG
        files = {"image": ("art.png", b"fake-png", "image/png")}
        response = client.post("/analyze", files=files)
        assert response.status_code == 200

        # Test WebP
        files = {"image": ("art.webp", b"fake-webp", "image/webp")}
        response = client.post("/analyze", files=files)
        assert response.status_code == 200

    def test_analyze_with_invalid_content_type(self, client: TestClient):
        """Test analyze endpoint rejects non-image files"""
        files = {"image": ("document.pdf", b"pdf-content", "application/pdf")}
        response = client.post("/analyze", files=files)

        assert response.status_code == 400
        assert "image" in response.json()["detail"].lower()

    def test_analyze_with_empty_file(self, client: TestClient):
        """Test analyze endpoint rejects empty files"""
        files = {"image": ("empty.png", b"", "image/png")}
        response = client.post("/analyze", files=files)

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_analyze_without_file(self, client: TestClient):
        """Test analyze endpoint requires file parameter"""
        response = client.post("/analyze")

        assert response.status_code == 422  # FastAPI validation error

    def test_analyze_with_openai_failure(self, client: TestClient, mock_openai_failure):
        """Test analyze endpoint handles OpenAI failures gracefully"""
        files = {"image": ("art.png", b"fake-image", "image/png")}
        response = client.post("/analyze", files=files)

        assert response.status_code == 500
        assert "detail" in response.json()

    def test_analyze_missing_api_key(self, client: TestClient, monkeypatch):
        """Test analyze endpoint requires API key"""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setattr(
            OpenAIFlags, "_default", None
        )  # force next get() to read env
        files = {"image": ("art.png", b"fake-image", "image/png")}
        response = client.post("/analyze", files=files)

        assert response.status_code == 500
        assert "API_KEY" in response.json()["detail"]

    def test_analyze_response_format(self, client: TestClient, mock_openai_success):
        """Test analyze endpoint returns correct response format"""
        files = {"image": ("art.png", b"fake-image", "image/png")}
        response = client.post("/analyze", files=files)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert "text" in data
        assert isinstance(data["text"], str)


class TestAnalyzeWithAuth:
    """Tests for analyze endpoint with authentication - similar to gagaou's auth tests"""

    def test_analyze_works_without_auth(self, client: TestClient, mock_openai_success):
        """Test analyze endpoint works without authentication"""
        files = {"image": ("art.png", b"fake-image", "image/png")}
        response = client.post("/analyze", files=files)

        assert response.status_code == 200

    def test_analyze_with_admin_auth(
        self, client: TestClient, mock_openai_success, auth_headers_admin
    ):
        """Test analyze endpoint works with admin authentication"""
        files = {"image": ("art.png", b"fake-image", "image/png")}
        response = client.post("/analyze", files=files, headers=auth_headers_admin)

        assert response.status_code == 200

    def test_analyze_with_client_auth(
        self, client: TestClient, mock_openai_success, auth_headers_client
    ):
        """Test analyze endpoint works with regular user authentication"""
        files = {"image": ("art.png", b"fake-image", "image/png")}
        response = client.post("/analyze", files=files, headers=auth_headers_client)

        assert response.status_code == 200


class TestAnalyzeApiClient:
    """Tests using the ApiClient wrapper - following gagaou's pattern"""

    def test_post_using_api_client(self, api_client: ApiClient, mock_openai_success):
        """Test using ApiClient wrapper for POST requests"""
        files = {"image": ("art.png", b"fake-image", "image/png")}
        response = api_client.post("/analyze", files=files)

        assert response.status_code == 200
        assert response.json()["text"] == "Mocked analyze output"

    def test_authenticated_request_using_api_client(
        self, api_client_auth: ApiClient, mock_openai_success
    ):
        """Test using authenticated ApiClient wrapper"""
        files = {"image": ("art.png", b"fake-image", "image/png")}
        response = api_client_auth.post("/analyze", files=files)

        assert response.status_code == 200
        assert response.json()["text"] == "Mocked analyze output"
