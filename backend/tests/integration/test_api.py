import base64


def test_health_check(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "museum-guide-backend"}


def test_analyze_endpoint(client, mock_openai_success):
    response = client.post(
        "/analyze",
        files={"image": ("art.png", b"png-bytes", "image/png")},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "Mocked analyze output"}


def test_tts_endpoint(client, mock_openai_success):
    response = client.post("/tts", json={"text": "Hello museum"})

    assert response.status_code == 200
    data = response.json()
    assert data["mime_type"] == "audio/mpeg"
    assert data["voice"] == "alloy"
    assert base64.b64decode(data["audio_base64"]) == b"fake-mp3-bytes"
