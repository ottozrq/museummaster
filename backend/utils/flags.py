import pathlib
import re
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field, model_validator
from pydantic.networks import HttpUrl

from utils.visionflags import Flags, Secret


class MuseumFlags(Flags):
    _visionflags_key = "museum"

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
    _visionflags_key = "museum_superuser"
    email: str = ""


class MuseumTestingFlags(Flags):
    _visionflags_key = "museum_testing"
    mode: bool = False

    @classmethod
    def get_testing_mode(cls) -> bool:
        return cls.get().mode
