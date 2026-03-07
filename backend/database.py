"""
Database engine and session for museum-guide-backend.
Uses DatabaseFlags (flags.yml + DATABASE_* env) for URL and echo.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from sql_models import Base
from utils.flags import DatabaseFlags

_db_flags = DatabaseFlags.get()
DATABASE_URL = _db_flags.url

# SQLite needs check_same_thread=False for FastAPI
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=_db_flags.sql_echo,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency: yield a DB session for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for non-FastAPI usage (e.g. scripts, migrations)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (optional; prefer Alembic migrations in production)."""
    Base.metadata.create_all(bind=engine)
