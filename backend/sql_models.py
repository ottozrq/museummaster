"""
SQL models (ORM) in a single module: base, mixins, helpers, and table classes.
Alembic discovers tables via Base.metadata; import Base, User, CollectionItem from here.
"""

import re
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.sqlite import CHAR
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
    relationship,
)

# ---------------------------------------------------------------------------
# Table name mixin: CamelCase -> snake_case
# ---------------------------------------------------------------------------


class _TableMixin:
    @declared_attr
    def __tablename__(cls) -> str:
        def _join(match: re.Match[str]) -> str:
            word = match.group()
            if len(word) > 1:
                return f"_{word[:-1]}_{word[-1]}".lower()
            return f"_{word.lower()}"

        pattern = re.compile(r"([A-Z]+)(?=[a-z0-9])")
        return pattern.sub(_join, cls.__name__).lstrip("_")


class _PostgresqlTableMixin(_TableMixin):
    """Gagaou-style: auto __tablename__ + inserted_at."""

    inserted_at: Mapped[datetime] = mapped_column(
        DateTime(True),
        server_default=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Base (reuse gagaou sqlbase, schema museum_sources)
# ---------------------------------------------------------------------------

MUSEUM_SCHEMA = "museum_sources"

PsqlBase = type(
    "PsqlBase",
    (DeclarativeBase, _PostgresqlTableMixin),
    {},
)


def _table_args():
    """Use schema museum_sources for PostgreSQL; omit for SQLite so default schema works."""
    try:
        from utils.flags import DatabaseFlags

        if "postgresql" in (DatabaseFlags.get().url or ""):
            return {"schema": MUSEUM_SCHEMA}
    except Exception:
        pass
    return {}


PsqlBase.__table_args__ = _table_args()

# Alias for code that imports Base
Base = PsqlBase


# ---------------------------------------------------------------------------
# Helpers (reusable column/relationship factories)
# ---------------------------------------------------------------------------

rel = relationship


def seq(name: str = "id"):
    """Auto-increment bigint primary key (PostgreSQL-friendly; SQLite uses Integer)."""
    return mapped_column(
        name,
        BigInteger,
        primary_key=True,
        autoincrement=True,
        unique=True,
    )


def enum_field(klass: type[Enum], nullable: bool = False, **kwargs: Any):
    return mapped_column(Enum(klass), nullable=nullable, **kwargs)


def uuid_field(
    name: Optional[str] = None,
    primary_key: bool = False,
    default: bool = False,
):
    """UUID column (CHAR(36) on SQLite; no server_default for portability)."""
    return mapped_column(
        *([name] if name else []),
        CHAR(36),
        primary_key=primary_key,
        default=lambda: str(uuid.uuid4()) if (default or primary_key) else None,
        unique=primary_key,
        nullable=False,
    )


def fk(
    foreign_field: str,
    nullable: bool = False,
    index: bool = True,
    ondelete: str = "CASCADE",
    **kwargs: Any,
):
    """Foreign key column."""
    return mapped_column(
        ForeignKey(foreign_field, ondelete=ondelete, onupdate="CASCADE"),
        nullable=nullable,
        index=index,
        **kwargs,
    )


def name_field(nullable: bool = False):
    return mapped_column(String, nullable=nullable)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class User(Base):
    """User account, linked to Apple Sign-In (sub)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    apple_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} apple_sub={self.apple_sub!r}>"


class CollectionItem(Base):
    """A single favorite/saved artwork for a user."""

    __tablename__ = "collection_items"

    id: Mapped[str] = mapped_column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    image_uri: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    audio_uri: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<CollectionItem id={self.id!r} user_id={self.user_id!r}>"


__all__ = [
    "Base",
    "PsqlBase",
    "MUSEUM_SCHEMA",
    "User",
    "CollectionItem",
    "rel",
    "seq",
    "enum_field",
    "uuid_field",
    "fk",
    "name_field",
    "_TableMixin",
    "_PostgresqlTableMixin",
]
