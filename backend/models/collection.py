"""API request/response models for collection (favorites)."""

from datetime import datetime

from pydantic import BaseModel, Field


class CollectionItemCreate(BaseModel):
    """Create a new collection item (favorite)."""

    image_uri: str | None = Field(default=None, max_length=2048)
    text: str = Field(..., min_length=1)
    audio_uri: str | None = Field(default=None, max_length=2048)


class CollectionItemUpdate(BaseModel):
    """Partial update for a collection item."""

    image_uri: str | None = Field(default=None, max_length=2048)
    text: str | None = Field(default=None, min_length=1)
    audio_uri: str | None = Field(default=None, max_length=2048)


class CollectionItemOut(BaseModel):
    """Collection item as returned by API."""

    id: str
    user_id: str
    image_uri: str | None
    text: str
    audio_uri: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
