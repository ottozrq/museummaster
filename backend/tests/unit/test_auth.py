"""Unit tests for POST /auth/apple (Apple Sign-In)."""

from unittest.mock import MagicMock

import jwt

from fastapi import HTTPException


def test_auth_apple_success(client, monkeypatch, test_secret):
    """Valid Apple identity token (mocked decode) returns our JWT."""
    from src.routes import auth as auth_module

    monkeypatch.setattr(
        auth_module,
        "_decode_apple_identity_token",
        MagicMock(return_value={"sub": "apple-sub-123"}),
    )
    response = client.post(
        "/auth/apple",
        json={"identity_token": "fake.apple.token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"
    payload = jwt.decode(
        data["access_token"],
        test_secret,
        algorithms=["HS256"],
    )
    assert payload.get("provider") == "apple"
    assert payload.get("role") == "user"
    assert "user_id" in payload


def test_auth_apple_missing_sub(client, monkeypatch):
    """Apple claims without sub return 400."""
    from src.routes import auth as auth_module

    monkeypatch.setattr(
        auth_module,
        "_decode_apple_identity_token",
        MagicMock(return_value={"aud": "dummy"}),
    )
    response = client.post(
        "/auth/apple",
        json={"identity_token": "fake.apple.token"},
    )
    assert response.status_code == 400
    assert "sub" in response.json()["detail"].lower()


def test_auth_apple_decode_error(client, monkeypatch):
    """Invalid token decode raises and is returned as 400/401."""
    from src.routes import auth as auth_module

    monkeypatch.setattr(
        auth_module,
        "_decode_apple_identity_token",
        MagicMock(
            side_effect=HTTPException(
                status_code=400,
                detail="Invalid Apple identity token header",
            )
        ),
    )
    response = client.post(
        "/auth/apple",
        json={"identity_token": "bad"},
    )
    assert response.status_code == 400
    assert "Invalid Apple" in response.json()["detail"]


def test_auth_apple_missing_body(client):
    response = client.post("/auth/apple", json={})
    assert response.status_code == 422
