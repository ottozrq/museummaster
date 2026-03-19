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

import models as m
import sql_models as sm
from utils import flags
from utils.utils import postgres_session


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
    role: sm.UserRole
    email: str
    user_uuid: uuid.UUID

    @classmethod
    def from_uuid(cls, user_uuid: uuid.UUID):
        try:
            with postgres_session() as db:
                return cls.from_user(m.User.db(db).from_id(user_uuid))
        except HTTPException:
            return cls(None, None, user_uuid)

    @classmethod
    def from_superuser(cls, superuser_email: str):
        with postgres_session() as db:
            return cls.from_user(
                m.User.from_db(
                    m.User.db(db).query.filter_by(user_email=superuser_email).one()
                )
            )

    @classmethod
    def from_user(cls, user: m.User):
        return cls(role=user.role, email=user.user_email, user_uuid=user.user_id)

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.email

    @property
    def role_string(self) -> str:
        return self.role or "uninitialized"


def handle_invalid_token_error(e: jwt.exceptions.InvalidTokenError):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=next(
            v
            for k, v in {
                jwt.exceptions.ExpiredSignatureError: "Token expired",
                jwt.exceptions.InvalidAudienceError: "Invalid audience",
                jwt.exceptions.InvalidIssuerError: "Invalid issuer",
                jwt.exceptions.InvalidIssuedAtError: "Invalid issued-at",
                jwt.exceptions.ImmatureSignatureError: "Immature signature",
                jwt.exceptions.InvalidAlgorithmError: "Invalid algorithm",
                jwt.exceptions.MissingRequiredClaimError: "Missing required claim: "
                + str(getattr(e, "claim", "")),
                jwt.exceptions.InvalidTokenError: "Invalid JWT token",
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
    except jwt.exceptions.InvalidTokenError as e:
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
        public_paths = [
            "/analyze",
            "/tts",
            "/auth",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/static",
        ]
        is_public_path = any(request.url.path.startswith(p) for p in public_paths)
        if superuser_email := _superuser_email():
            return MuseumAuthUser.from_superuser(superuser_email)
        if request.url.path == "/token/":
            return None
        has_auth_header = (
            "Authorization" in request.headers or "authorization" in request.headers
        )
        # public path 允许匿名访问；但如果带了 Authorization，仍应解析用户，
        # 这样下游（如 /analyze）才能拿到 request.user 并写入 user_id。
        if is_public_path and not has_auth_header:
            return None
        if not has_auth_header:
            return None
        return MuseumAuthUser.from_uuid(
            _get_user_uuid(await OAuth2PasswordBearer("/token/").__call__(request))
        )


def _superuser_email():
    return flags.MuseumFlags.get().superuser_email
