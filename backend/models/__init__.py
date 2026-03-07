"""
Pydantic models for API request/response (schemas).
Separate from sql_models (ORM); use these for validation and serialization.
"""

from models.auth import AppleLoginRequest, TokenResponse
from models.collection import (
    CollectionItemCreate,
    CollectionItemOut,
    CollectionItemUpdate,
)

__all__ = [
    "AppleLoginRequest",
    "TokenResponse",
    "CollectionItemCreate",
    "CollectionItemOut",
    "CollectionItemUpdate",
]
