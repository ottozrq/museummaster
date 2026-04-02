"""Unit tests for POST /analyze (artwork analysis)."""

import base64
from datetime import datetime, timedelta

import jwt

import sql_models as sm
from src.routes.analyze import _analyze_prompt, _normalize_analyze_locale
from utils.flags import MuseumFlags
from utils.subscription import consume_quota_after_success, get_active_plan


def test_normalize_analyze_locale():
    assert _normalize_analyze_locale(None) == "zh"
    assert _normalize_analyze_locale("") == "zh"
    assert _normalize_analyze_locale("en-US") == "en"
    assert _normalize_analyze_locale("zh-Hans-CN") == "zh"
    assert _normalize_analyze_locale("fr-CA") == "fr"
    assert _normalize_analyze_locale("de") == "en"


def test_analyze_prompt_matches_language_family():
    assert "中文" in _analyze_prompt("zh")
    assert "in English" in _analyze_prompt("en")
    assert "en français" in _analyze_prompt("fr")


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
    """When Gemini api_key is empty, endpoint returns 500
    with API_KEY in detail."""
    from types import SimpleNamespace

    from utils.flags import GeminiFlags

    fake_flags = SimpleNamespace(
        api_key="",
        model="gemini-2.5-flash",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    monkeypatch.setattr(
        GeminiFlags,
        "get",
        classmethod(lambda cls: fake_flags),
    )
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
    api_client_editor, mock_openai_success, sample_image_bytes
):
    user_id = str(api_client_editor.user.user_id)
    _seed_scan_records(api_client_editor.session, user_id, 4)

    files = {"image": ("art.png", sample_image_bytes, "image/png")}
    response = api_client_editor.post("/analyze", files=files)
    assert response.status_code == 200


def test_analyze_daily_quota_blocks_6th(
    api_client_editor, mock_openai_success, sample_image_bytes
):
    user_id = str(api_client_editor.user.user_id)
    _seed_scan_records(api_client_editor.session, user_id, 5)

    files = {"image": ("art.png", sample_image_bytes, "image/png")}
    response = api_client_editor.post("/analyze", files=files, status=429)
    detail = response.json()["detail"]
    assert isinstance(detail, dict)
    assert "quota" in (detail.get("message") or "").lower()


def test_analyze_admin_unlimited(api_client, mock_openai_success, sample_image_bytes):
    user_id = str(api_client.user.user_id)
    _seed_scan_records(api_client.session, user_id, 5)

    files = {"image": ("art.png", sample_image_bytes, "image/png")}
    response = api_client.post("/analyze", files=files)
    assert response.status_code == 200


def test_analyze_scan_pack_consumes_remaining(
    api_client_editor, mock_openai_success, sample_image_bytes
):
    user_id = str(api_client_editor.user.user_id)
    user_db = (
        api_client_editor.session.query(sm.User)
        .filter(sm.User.user_id == user_id)
        .one()
    )
    user_db.extras = {
        "subscription": {
            "type": "scan_pack",
            "scan_pack_total": 50,
            "scan_pack_remaining": 1,
        }
    }
    api_client_editor.session.add(user_db)
    api_client_editor.session.commit()
    sub0 = user_db.extras.get("subscription") or {}
    assert isinstance(sub0.get("scan_pack_remaining"), (int, float))

    quota0 = api_client_editor("/scan-quota/remaining")
    assert quota0.status_code == 200
    q = quota0.json()
    assert q.get("plan") == "scan_pack"
    assert q.get("remaining") == 1

    # 第一次应允许，且成功后扣减 scan_pack_remaining
    files = {"image": ("art.png", sample_image_bytes, "image/png")}
    ok = api_client_editor.post("/analyze", files=files)
    assert ok.status_code == 200

    quota1 = api_client_editor("/scan-quota/remaining")
    q1 = quota1.json()
    assert q1.get("plan") == "free"
    # free 每日 5 次，用掉 1 次后剩余 4 次
    assert q1.get("remaining") == 4

    api_client_editor.session.refresh(user_db)
    sub = user_db.extras.get("subscription") or {}
    assert sub.get("scan_pack_remaining") == 0


def test_analyze_pro_unlimited_overrides_free_daily(
    api_client_editor, mock_openai_success, sample_image_bytes
):
    user_id = str(api_client_editor.user.user_id)

    # free 每日 5 次：先把额度用满
    _seed_scan_records(api_client_editor.session, user_id, 5)

    # 激活 pro，pro 不受每日额度影响
    expires_ts = int((datetime.utcnow() + timedelta(days=40)).timestamp())
    user_db = (
        api_client_editor.session.query(sm.User)
        .filter(sm.User.user_id == user_id)
        .one()
    )
    user_db.extras = {
        "subscription": {
            "type": "pro_monthly",
            "pro_expires_at_ts": expires_ts,
            "pro_scan_total": 200,
            "pro_scan_remaining": 200,
        }
    }
    api_client_editor.session.add(user_db)
    api_client_editor.session.commit()

    files = {"image": ("art.png", sample_image_bytes, "image/png")}
    response = api_client_editor.post("/analyze", files=files)
    assert response.status_code == 200


def test_consume_quota_scan_pack_decrements_remaining(api_client_editor):
    user_id = str(api_client_editor.user.user_id)
    user_db = (
        api_client_editor.session.query(sm.User)
        .filter(sm.User.user_id == user_id)
        .one()
    )
    user_db.extras = {
        "subscription": {
            "type": "scan_pack",
            "scan_pack_total": 50,
            "scan_pack_remaining": 1,
        }
    }
    api_client_editor.session.add(user_db)
    api_client_editor.session.commit()

    assert get_active_plan(user_db) == "scan_pack"

    consume_quota_after_success(user_db, api_client_editor.db)
    refreshed = (
        api_client_editor.session.query(sm.User)
        .filter(sm.User.user_id == user_id)
        .one()
    )
    sub_after = refreshed.extras.get("subscription") or {}
    assert sub_after.get("scan_pack_remaining") == 0
    api_client_editor.session.commit()

    api_client_editor.session.refresh(user_db)
    sub = user_db.extras.get("subscription") or {}
    assert sub.get("scan_pack_remaining") == 0


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
    detail = blocked.json()["detail"]
    assert isinstance(detail, dict)
    assert "quota" in (detail.get("message") or "").lower()


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
