import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal

from fastapi import Request, status
from fastapi.exceptions import HTTPException
from pydantic import ConfigDict
from pydantic.types import NonNegativeInt
from sqlalchemy.orm import session

import sql_models as sm
from utils import flags
from utils.auto_enum import AutoEnum, auto
from utils.museummodels import AutoLink, Link, Model
from utils.utils import MuseumDb


class OpenAPITag(AutoEnum):
    Users = auto()
    Root = auto()
    Analyze = auto()
    TTS = auto()
    Auth = auto()


class Kind(AutoEnum):
    user = auto()

    @property
    def plural(self) -> str:
        return {}.get(self, f"{self.value}s")

    @property
    def root(self) -> Link:
        return Path("/") / self.plural

    def link(self, id_value: str) -> Link:
        return self.root / str(id_value)

    def __str__(self) -> str:
        return self.value


@dataclass
class Pagination:
    request: Request
    page_size: NonNegativeInt
    page_token: str


@dataclass
class EntityQuery:
    db: MuseumDb
    entity: "Entity"

    @property
    def query(self):
        return self.entity.query(self.session)

    @property
    def session(self):
        return self.db.session

    def get_or_404(self, primary_key):
        return self.entity.get_or_404(self.session, primary_key)

    def get_or_none(self, primary_key):
        return self.entity.get_or_none(self.session, primary_key)

    def from_id(self, id_value):
        return self.entity.from_db(self.get_or_404(id_value))


class Entity(Model):
    model_config = ConfigDict(extra="allow", kind=None, db_model=None)
    self_link: Link
    kind: Kind

    def __truediv__(self, path: Path) -> Path:
        return self.self_link / path

    @classmethod
    def self_link_prefix(cls, value) -> Path:
        return cls.model_config.get("kind").root

    @classmethod
    def db(cls, db):
        return EntityQuery(db, cls)

    @classmethod
    def query(cls, session: session.Session):
        return session.query(cls.model_config.get("db_model"))

    @classmethod
    def _get(cls, session: session.Session, primary_key):
        return cls.query(session).get(cls._to_id(primary_key))

    @classmethod
    def get_or_404(cls, session, primary_key):
        record = cls._get(session, primary_key)
        if not record:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found")
        return record

    @classmethod
    def from_db_list(cls, xs: List[sm.PsqlBase], **forward_args):
        return [cls.from_db(x, **forward_args) for x in xs]

    @classmethod
    def _to_id(cls, x):
        if isinstance(x, uuid.UUID):
            return str(x)
        return x

    @classmethod
    def link(cls, item, field=None):
        if item is None:
            return None
        if isinstance(item, Path):
            return item
        instance_id = (
            item
            if type(item) in {str, int, float, uuid.UUID}
            else getattr(item, field) if field is not None else cls._extract_id(item)
        )
        return cls.self_link_prefix(item) / str(instance_id)

    @classmethod
    def _extract_id(cls, item):
        return next(
            (
                getattr(item, field)
                for field in cls._id_fields()
                if hasattr(item, field)
            ),
            None,
        )

    @classmethod
    def _id_fields(cls):
        return (f"{cls.model_config['kind'].value}_id",)

    @classmethod
    def links(
        cls,
        instance: Union[Request, sm.PsqlBase],
        *args,
        id_value: str = None,
        self_link: Link = None,
    ):
        kind = cls.model_config.get("kind")
        if id_value:
            self_link = kind.link(id_value)
        elif not self_link and instance:
            if isinstance(instance, Request):
                self_link_str = instance.url.path.rstrip("/")
                if root_path := flags.MuseumFlags.get().root_path:
                    self_link_str = re.sub(rf"^{str(root_path)}", "", self_link_str)
                self_link = Path(self_link_str)
            else:
                instance_id = cls._extract_id(instance)
                self_link = cls.self_link_prefix(instance) / str(instance_id)
        return dict(
            self_link=self_link,
            kind=kind,
            **{
                arg: self_link / str(arg)
                for arg in {
                    x
                    for y in [
                        args,
                        {
                            v.alias or k
                            for k, v in cls.model_fields.items()
                            if v.annotation is AutoLink
                        },
                    ]
                    for x in y
                }
            },
        )




class UserPatch(Model):
    first_name: str = None
    last_name: str = None
    role: sm.UserRole = None
    extras: Dict[str, Any] = {}


class UserBase(UserPatch):
    user_email: str
    first_name: str = ""
    last_name: str = ""
    role: sm.UserRole = sm.UserRole.client
    extras: Dict[str, Any] = {}


class UserCreate(UserBase):
    password: str


class User(Entity, UserBase):
    user_id: uuid.UUID
    date_joined: datetime = None

    class Config:
        db_model = sm.User
        kind = Kind.user

    @classmethod
    def from_db(cls, user: sm.User):
        return cls(
            user_id=user.user_id,
            first_name=user.first_name,
            last_name=user.last_name,
            user_email=user.user_email,
            date_joined=user.date_joined,
            extras=user.extras,
            role=user.role,
            **cls.links(user),
        )


class LoginResponse(Model):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


# ---------------------------------------------------------------------------
# Auth (Apple login) and TTS request/response
# ---------------------------------------------------------------------------


class AppleLoginRequest(Model):
    """Body for POST /auth/apple.

    Apple 只在用户第一次同意时返回 fullName，之后多次登录时 fullName 可能为空，
    所以 first_name/last_name 为可选，仅在创建新用户时使用。
    """

    identity_token: str
    first_name: str | None = None
    last_name: str | None = None


class TokenResponse(Model):
    """Response after successful Apple login."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"


class TTSRequest(Model):
    """Body for POST /tts."""

    text: str
