# import pathlib
import re
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship

from utils.auto_enum import AutoEnum, auto

# from typing import Any, Dict, List


class _tablemixin:
    @declared_attr
    def __tablename__(cls):
        def _join(match):
            word = match.group()

            if len(word) > 1:
                return f"_{word[:-1]}_{word[-1]}".lower()

            return f"_{word.lower()}"

        return re.compile(r"([A-Z]+)(?=[a-z0-9])").sub(_join, cls.__name__).lstrip("_")


class _postgresql_tablemixin(_tablemixin):
    inserted_at = Column(DateTime(True), server_default=func.now(), nullable=False)


PsqlBase = declarative_base(cls=_postgresql_tablemixin)
PsqlBase.__table_args__ = {"schema": "museum_sources"}

rel = relationship


def seq(name):
    return Column(name, BigInteger, primary_key=True, autoincrement=True, unique=True)


def enum_field(klass, nullable=False, **kwargs):
    return Column(Enum(klass), nullable=nullable, **kwargs)


def uuid_field(name=None, primary_key=False, default=False):
    return Column(
        *([name] if name else []),
        UUID(as_uuid=False),
        primary_key=primary_key,
        server_default=func.uuid_generate_v4(),
        default=uuid.uuid4 if default else None,
        unique=True,
        nullable=False,
    )


def fk(foreign_field, nullable=False, index=True, ondelete="CASCADE", **kwargs):
    return Column(
        None,
        ForeignKey(
            foreign_field,
            ondelete=ondelete,
            onupdate="CASCADE",
        ),
        nullable=nullable,
        index=index,
        **kwargs,
    )


def name_field(nullable=False):
    return Column(
        String,
        nullable=nullable,
    )


class UserRole(AutoEnum):
    admin = auto()
    client = auto()


class User(PsqlBase):
    user_id = uuid_field(primary_key=True)
    user_email = Column(
        String,
        unique=True,
        nullable=False,
    )
    password = Column(String, nullable=False)
    first_name = name_field()
    last_name = name_field()
    date_joined = Column(DateTime(True), nullable=False, server_default=func.now())
    is_superuser = Column(Boolean, server_default="FALSE", nullable=False)
    role = enum_field(UserRole, server_default=UserRole.client, nullable=False)
    extras = Column(JSON, nullable=True)


class CollectionItem(PsqlBase):
    """A single favorite/saved artwork for a user."""

    id = uuid_field(primary_key=True)
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("museum_sources.user.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_uri = Column(String(2048), nullable=True)
    text = Column(Text, nullable=False)
    audio_uri = Column(String(2048), nullable=True)
    created_at = Column(DateTime(True), nullable=False, server_default=func.now())
