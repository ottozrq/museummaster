"""Apple Sign-In and token response."""

import json
import urllib.request
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status

import depends as d
import models as m
import sql_models as sm
from src.routes import TAG, app
from utils import flags
from utils.flags import AppleFlags
from utils.utils import MuseumDb

APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"


def _get_apple_public_key(identity_token: str):
    """从 Apple 公钥列表中找到与 identity token 匹配的公钥"""
    try:
        header = jwt.get_unverified_header(identity_token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Apple identity token header",
        ) from exc

    kid = header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apple identity token missing 'kid' header",
        )

    try:
        with urllib.request.urlopen(APPLE_KEYS_URL, timeout=5) as resp:
            jwks = json.load(resp)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to fetch Apple public keys",
        ) from exc

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No matching Apple public key found",
    )


def _decode_apple_identity_token(identity_token: str) -> dict:
    """验证并解码 Apple 的 identity token，返回 claims"""
    public_key = _get_apple_public_key(identity_token)
    client_id = AppleFlags.get().client_id
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="APPLE_CLIENT_ID is not configured",
        )

    try:
        claims = jwt.decode(
            identity_token,
            key=public_key,
            algorithms=["RS256"],
            audience=client_id,
            issuer="https://appleid.apple.com",
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Apple identity token expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Apple identity token",
        ) from exc

    return claims


@app.post("/auth/apple", response_model=m.TokenResponse, tags=[TAG.Auth])
def login_with_apple(
    payload: m.AppleLoginRequest,
    db: MuseumDb = Depends(d.get_psql),
) -> m.TokenResponse:
    """
    使用 Apple 登录：
    - 验证 Apple identity token
    - 用 Apple 的 user id 生成稳定的 UUID
    - 用项目自己的 login_secret 签发 JWT
    """
    claims = _decode_apple_identity_token(payload.identity_token)
    apple_sub = claims.get("sub")
    if not apple_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apple identity token missing 'sub' claim",
        )

    # Find or create a local User linked to this Apple account.
    # We use a pseudo email "apple:{sub}" to avoid touching the normal email/password flow.
    pseudo_email = f"apple:{apple_sub}"
    session = db.session
    user = (
        session.query(sm.User).filter(sm.User.user_email == pseudo_email).one_or_none()
    )
    if not user:
        user = sm.User(
            user_email=pseudo_email,
            password="",
            first_name=payload.first_name or "",
            last_name=payload.last_name or "",
            extras={"provider": "apple", "apple_sub": apple_sub},
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    user_uuid = user.user_id
    MF = flags.MuseumFlags.get()
    now = datetime.utcnow()
    exp = now + timedelta(days=30)

    token_payload = {
        "user_id": str(user_uuid),
        "role": "user",
        "provider": "apple",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    encoded = jwt.encode(token_payload, MF.login_secret, algorithm="HS256")
    return m.TokenResponse(access_token=encoded)
