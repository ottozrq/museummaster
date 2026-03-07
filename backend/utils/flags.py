import pathlib
import re
from typing import Annotated, List, Optional

from pydantic import Field
from pydantic.networks import HttpUrl

from utils.museumflags import Flags

# ---------------------------------------------------------------------------
# Environment / service flags (gagaou-style: one place for all env-driven config)
# ---------------------------------------------------------------------------


class DatabaseFlags(Flags):
    """Database connection and behavior. Env: DATABASE_* (e.g. DATABASE_URL)."""

    _museumflags_key = "database"

    url: str = "sqlite:///./museum.db"
    sql_echo: bool = False


class OpenAIFlags(Flags):
    """OpenAI API keys and model names. Env: OPENAI_*."""

    _museumflags_key = "openai"

    api_key: str = ""
    museum_model: str = "gpt-4o"
    tts_model: str = "gpt-4o-mini-tts"
    tts_voice: str = "alloy"


class AppleFlags(Flags):
    """Apple Sign-In. Env: APPLE_* (e.g. APPLE_CLIENT_ID)."""

    _museumflags_key = "apple"

    client_id: str = ""


# ---------------------------------------------------------------------------
# App / auth flags (existing)
# ---------------------------------------------------------------------------


class MuseumFlags(Flags):
    _museumflags_key = "museum"

    namespace: Annotated[str, Field(alias="namespace")]
    login_secret: str = "default_secret_change_me"
    google_client_id: str = ""

    cors_urls: List[HttpUrl] = []

    display_traceback: bool = False
    debug: bool = False
    testing_mode: bool = False

    root_path: Optional[pathlib.Path] = None

    allow_origin_regex: re.Pattern = re.compile(
        r"^(http://(.*\.)?localhost:\d+|https://.*\.museum\.(dev|io))/?$"
    )

    @property
    def superuser_email(self) -> str:
        return MuseumSuperuserFlags.get().email


class MuseumSuperuserFlags(Flags):
    _museumflags_key = "museum_superuser"
    email: str = ""


class MuseumTestingFlags(Flags):
    _museumflags_key = "museum_testing"
    mode: bool = False

    @classmethod
    def get_testing_mode(cls) -> bool:
        return cls.get().mode


# ---------------------------------------------------------------------------
# Convenience: export env var names for documentation / .env.example
# ---------------------------------------------------------------------------
# DatabaseFlags -> DATABASE_URL, DATABASE_SQL_ECHO
# OpenAIFlags   -> OPENAI_API_KEY, OPENAI_MUSEUM_MODEL, OPENAI_TTS_MODEL, OPENAI_TTS_VOICE
# AppleFlags    -> APPLE_CLIENT_ID
# MuseumFlags   -> MUSEUM_* (namespace, login_secret, ...)
