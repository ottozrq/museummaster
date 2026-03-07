"""API request/response models for auth (e.g. Apple login)."""

from pydantic import BaseModel, Field


class AppleLoginRequest(BaseModel):
    """Body for POST /auth/apple."""

    identity_token: str = Field(..., description="Apple identity token (JWT)")


class TokenResponse(BaseModel):
    """Response after successful login."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
