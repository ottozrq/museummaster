"""Unit tests for Apple Sign-In backend endpoint (/auth/apple).

这里的测试重点是验证：
- 当 Apple 身份验证成功时，我们是否正确签发应用自己的 JWT
- 当 Apple 返回的 claims 缺少关键信息时，是否返回合适的错误码
- 当 Apple token 本身无效时，是否将错误向上抛出

为了避免依赖真实的 Apple 公钥和加密逻辑，这里的测试会直接
mock 掉 `_decode_apple_identity_token`，只聚焦我们自己的业务逻辑。
"""

from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import HTTPException

APPLE_IDENTITY_TOKEN = "fake.apple.identity.token"


class TestAppleAuth:
    """Tests for /auth/apple endpoint (function-level)."""

    def test_login_with_apple_success(
        self,
        monkeypatch,
        test_secret,
    ):
        """Happy path: valid identity token returns our own JWT."""
        import routers.auth as auth_module

        # 模拟 Apple 解码成功，返回包含 sub 的 claims
        monkeypatch.setattr(
            auth_module,
            "_decode_apple_identity_token",
            MagicMock(return_value={"sub": "apple-sub-id-123"}),
        )

        req = auth_module.AppleLoginRequest(identity_token=APPLE_IDENTITY_TOKEN)
        resp = auth_module.login_with_apple(req)

        assert resp.access_token
        assert resp.token_type == "bearer"

        # Verify returned token payload structure
        payload = jwt.decode(
            resp.access_token,
            test_secret,
            algorithms=["HS256"],
        )
        assert payload["provider"] == "apple"
        assert payload["role"] == "user"
        # user_id should be a UUID string derived from Apple sub
        assert isinstance(payload["user_id"], str)

    def test_login_with_apple_missing_sub(
        self,
        monkeypatch,
    ):
        """If Apple token doesn't contain sub claim, raise 400."""
        import routers.auth as auth_module

        # Apple claims 缺少 sub
        monkeypatch.setattr(
            auth_module,
            "_decode_apple_identity_token",
            MagicMock(return_value={"aud": "dummy"}),
        )

        req = auth_module.AppleLoginRequest(identity_token=APPLE_IDENTITY_TOKEN)
        with pytest.raises(HTTPException) as exc:
            auth_module.login_with_apple(req)

        assert exc.value.status_code == 400
        assert exc.value.detail == "Apple identity token missing 'sub' claim"

    def test_login_with_apple_invalid_header(
        self,
        monkeypatch,
    ):
        """Invalid identity token header should bubble up 400."""
        import routers.auth as auth_module

        # 模拟内部解码逻辑抛出 400 错误（例如 header 无效）
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

        req = auth_module.AppleLoginRequest(identity_token=APPLE_IDENTITY_TOKEN)
        with pytest.raises(HTTPException) as exc:
            auth_module.login_with_apple(req)

        assert exc.value.status_code == 400
        assert "Invalid Apple identity token header" in exc.value.detail
