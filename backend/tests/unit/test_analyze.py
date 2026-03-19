"""Unit tests for POST /analyze (artwork analysis)."""

import base64
from datetime import datetime, timedelta

import jwt

import sql_models as sm
from utils.flags import MuseumFlags


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


def _seed_scan_records(session, user_id: str, count: int) -> None:
    for _ in range(count):
        session.add(
            sm.ScanRecord(
                user_id=user_id,
                artwork_code="unknown",
                image_path="/static/test-scan.jpg",
                text="seed",
                audio_path=None,
            )
        )
    session.commit()


def test_analyze_daily_quota_allows_up_to_5(
    api_client, mock_openai_success, sample_image_bytes
):
    user_id = str(api_client.user.user_id)
    _seed_scan_records(api_client.session, user_id, 4)

    files = {"image": ("art.png", sample_image_bytes, "image/png")}
    response = api_client.post("/analyze", files=files)
    assert response.status_code == 200


def test_analyze_daily_quota_blocks_6th(
    api_client, mock_openai_success, sample_image_bytes
):
    user_id = str(api_client.user.user_id)
    _seed_scan_records(api_client.session, user_id, 5)

    files = {"image": ("art.png", sample_image_bytes, "image/png")}
    response = api_client.post("/analyze", files=files, status=429)
    assert response.json()["detail"].lower().find("quota") >= 0


def _create_committed_user(client, email: str) -> sm.User:
    """Create a user in the same app DB used by TestClient requests."""
    session = client.app.postgres_sessionmaker.SessionLocal()
    try:
        user = sm.User(
            user_email=email,
            password="pw",
            first_name="",
            last_name="",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


def _make_access_token(user_id: str) -> str:
    MF = MuseumFlags.get()
    now = datetime.utcnow()
    exp = now + timedelta(days=30)
    payload = {
        "user_id": str(user_id),
        "role": "user",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, MF.login_secret, algorithm="HS256")


def test_analyze_http_saves_user_id_when_authorized(
    client, mock_openai_success, sample_image_bytes
):
    user = _create_committed_user(client, "http_user@example.com")
    token = _make_access_token(user.user_id)

    files = {"image": ("art.png", sample_image_bytes, "image/png")}
    for _ in range(5):
        rec = client.post(
            "/analyze",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rec.status_code == 200

    blocked = client.post(
        "/analyze",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert blocked.status_code == 429
    assert "quota" in blocked.json()["detail"].lower()


def test_analyze_ws_saves_user_id_when_authorized(
    client, mock_openai_success, sample_image_bytes
):
    user = _create_committed_user(client, "ws_user@example.com")
    token = _make_access_token(user.user_id)

    image_base64 = base64.b64encode(sample_image_bytes).decode("utf-8")

    def _ws_once():
        with client.websocket_connect(
            "/analyze",
            headers={"Authorization": f"Bearer {token}"},
        ) as ws:
            ws.send_json(
                {
                    "type": "start",
                    "image_base64": image_base64,
                    "mime_type": "image/png",
                    "auth_token": token,
                }
            )
            while True:
                msg = ws.receive_json()
                if msg.get("type") == "done":
                    return ("done", msg)
                if msg.get("type") == "error":
                    return ("error", msg)

    for _ in range(5):
        kind, payload = _ws_once()
        assert kind == "done"
        assert payload.get("scan_id") is not None

    kind, payload = _ws_once()
    assert kind == "error"
    assert payload.get("code") == "DAILY_SCAN_QUOTA_EXCEEDED"
    assert "quota" in str(payload.get("message", "")).lower()
