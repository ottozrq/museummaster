"""Unit tests for POST /analyze (artwork analysis)."""


def test_analyze_success(client, mock_openai_success, sample_image_bytes):
    files = {"image": ("art.png", sample_image_bytes, "image/png")}
    response = client.post("/analyze", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert data["text"] == "Mocked analyze output"
    assert "scan_id" in data
    assert isinstance(data["scan_id"], str)


def test_analyze_accepts_jpeg(client, mock_openai_success):
    files = {"image": ("art.jpg", b"fake-jpeg", "image/jpeg")}
    response = client.post("/analyze", files=files)
    assert response.status_code == 200
    assert response.json()["text"] == "Mocked analyze output"


def test_analyze_rejects_non_image(client):
    files = {"image": ("doc.pdf", b"pdf", "application/pdf")}
    response = client.post("/analyze", files=files)
    assert response.status_code == 400
    assert "image" in response.json()["detail"].lower()


def test_analyze_rejects_empty_file(client):
    files = {"image": ("empty.png", b"", "image/png")}
    response = client.post("/analyze", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_analyze_without_file(client):
    response = client.post("/analyze")
    assert response.status_code == 422


def test_analyze_openai_failure(client, mock_openai_failure, sample_image_bytes):
    files = {"image": ("art.png", sample_image_bytes, "image/png")}
    response = client.post("/analyze", files=files)
    assert response.status_code == 500
    assert "detail" in response.json()


def test_analyze_missing_api_key(client, monkeypatch, sample_image_bytes):
    """When OpenAI api_key is empty, endpoint returns 500 with API_KEY in detail."""
    from types import SimpleNamespace

    from utils.flags import OpenAIFlags

    fake_flags = SimpleNamespace(api_key="", museum_model="gpt-4o")
    monkeypatch.setattr(OpenAIFlags, "get", classmethod(lambda cls: fake_flags))
    files = {"image": ("art.png", sample_image_bytes, "image/png")}
    response = client.post("/analyze", files=files)
    assert response.status_code == 500
    assert "API_KEY" in response.json()["detail"]
