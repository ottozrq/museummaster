import logging
import uuid
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    BaseUser,
)
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse, Response

from utils import flags


@dataclass
class MuseumAuthenticationError(AuthenticationError):
    content: dict
    status_code: status


def authentication_on_error(
    conn: HTTPConnection, e: MuseumAuthenticationError
) -> Response:
    return JSONResponse(content=e.content, status_code=e.status_code)


@dataclass(frozen=True)
class MuseumAuthUser(BaseUser):
    role: str
    email: str
    user_uuid: uuid.UUID

    @classmethod
    def from_uuid(cls, user_uuid: uuid.UUID):
        # Simplified version - in production, would query database
        return cls(role="user", email="user@example.com", user_uuid=user_uuid)

    @classmethod
    def from_superuser(cls, superuser_email: str):
        return cls(role="superuser", email=superuser_email, user_uuid=uuid.uuid4())

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.email

    @property
    def role_string(self) -> str:
        return self.role or "uninitialized"


def handle_invalid_token_error(e: jwt.InvalidTokenError):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=next(
            v
            for k, v in {
                jwt.InvalidTokenError: "Invalid JWT token",
                jwt.ExpiredSignatureError: "Token expired",
                jwt.InvalidSignatureError: "Invalid signature",
                jwt.DecodeError: "Token decode error",
            }.items()
            if isinstance(e, k)
        ),
    )


def _get_user_uuid(token):
    MF = flags.MuseumFlags.get()
    try:
        try:
            return uuid.UUID(
                jwt.decode(token, MF.login_secret, algorithms=["HS256"])["user_id"]
            )
        except jwt.InvalidSignatureError:
            pass
    except jwt.InvalidTokenError as e:
        handle_invalid_token_error(e)
    except Exception as e:
        logging.getLogger(__name__).exception("Failed to parse JWT", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to parse credentials/incorrect format",
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


class MuseumAuthBackend(AuthenticationBackend):
    async def authenticate(self, request):
        try:
            if user := await self.museum_user(request):
                return AuthCredentials(["authenticated"]), user
        except HTTPException as e:
            raise MuseumAuthenticationError(
                content=dict(detail=e.detail),
                status_code=e.status_code,
            )

    async def museum_user(self, request) -> MuseumAuthUser:
        # Public endpoints that don't require authentication
        public_paths = ["/analyze", "/tts", "/docs", "/openapi.json", "/redoc"]
        if any(request.url.path.startswith(p) for p in public_paths):
            return None
        
        if superuser_email := _superuser_email():
            return MuseumAuthUser.from_superuser(superuser_email)
        if "Authorization" not in request.headers or request.url.path == "/token/":
            return None
        return MuseumAuthUser.from_uuid(
            _get_user_uuid(await OAuth2PasswordBearer("/token/").__call__(request))
        )


def _superuser_email() -> str:
    return flags.MuseumFlags.get().superuser_email
