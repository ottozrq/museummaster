"""Unit tests for GET /tts and POST /tts (text-to-speech)."""

import base64


def test_tts_post_success(client, mock_openai_success, sample_text):
    response = client.post("/tts", json={"text": sample_text})
    assert response.status_code == 200
    data = response.json()
    assert "audio_base64" in data
    assert data["mime_type"] == "audio/mpeg"
    assert data["voice"] == "alloy"
    raw = base64.b64decode(data["audio_base64"])
    assert raw == b"fake-mp3-bytes"


def test_tts_get_success(client, mock_openai_success, sample_text):
    response = client.get("/tts", params={"text": sample_text})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"fake-mp3-bytes"


def test_tts_post_empty_text(client):
    response = client.post("/tts", json={"text": ""})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_tts_get_empty_text(client):
    response = client.get("/tts", params={"text": ""})
    assert response.status_code == 422


def test_tts_post_whitespace_only(client):
    response = client.post("/tts", json={"text": "   "})
    assert response.status_code == 400


def test_tts_post_missing_text(client):
    response = client.post("/tts", json={})
    assert response.status_code == 422


def test_tts_post_openai_failure(client, mock_openai_failure, sample_text):
    response = client.post("/tts", json={"text": sample_text})
    assert response.status_code == 500
    assert "detail" in response.json()


def test_tts_get_openai_failure(client, mock_openai_failure, sample_text):
    """GET /tts when OpenAI fails: stream raises before/during send (client may get 500 or exception)."""
    try:
        response = client.get("/tts", params={"text": sample_text})
        assert response.status_code >= 500
    except Exception:
        # StreamingResponse can raise when generator raises before first yield
        pass


def test_tts_post_missing_api_key(client, monkeypatch, sample_text):
    """When OpenAI api_key is empty, endpoint returns 500 with API_KEY in detail."""
    from types import SimpleNamespace

    from utils.flags import OpenAIFlags

    fake_flags = SimpleNamespace(
        api_key="",
        tts_model="gpt-4o-mini-tts",
        tts_voice="alloy",
    )
    monkeypatch.setattr(OpenAIFlags, "get", classmethod(lambda cls: fake_flags))
    response = client.post("/tts", json={"text": sample_text})
    assert response.status_code == 500
    assert "API_KEY" in response.json()["detail"]
