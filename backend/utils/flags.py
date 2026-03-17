import pathlib
import re
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field, model_validator
from pydantic.networks import EmailStr, HttpUrl

from utils.museumflags import Flags, Secret


class PostgresqlFlags(Flags):
    _museumflags_key = "museum_pg"

    host: str

    password: str = Secret("aurora_cluster_master_password")

    database: str = "museum"
    schema_prefix: str = "museum_sources"
    username: str = "museum"

    ssl_mode: bool = True

    @property
    def url(self):
        from sqlalchemy.engine.url import URL

        return URL.create(
            drivername="postgresql",
            username=self.username,
            host=self.host,
            database=self.database,
            port=5432,
            password=self.password,
        )


class SqlAlchemyFlags(Flags):
    _museumflags_key = "sqlalchemy"

    echo: bool = False
    track_modifications: bool = False
    alembic_env: Optional[str] = None


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


class MuseumSuperuserFlags(Flags):
    _museumflags_key = "museum_superuser"
    email: EmailStr = ""


class MuseumTestingFlags(Flags):
    _museumflags_key = "museum_testing"
    mode: bool = False


class MuseumFlags(Flags):
    _museumflags_key = "museum"

    namespace: Annotated[str, Field(alias="namespace")] = "museum-local"
    login_secret: str = "change_me_in_local"
    google_client_id: str = ""

    # cognito_cert_1: str = Secret("jwt_public_key_cognito_1")
    # cognito_cert_2: str = Secret("jwt_public_key_cognito_2")
    # salt: str = Secret("salt")

    # eb_endpoint: str = "http://localhost:4572"
    # lambda_endpoint: str = "https://lambda.eu-central-1.amazonaws.com"
    # sm_endpoint: str = "https://secretsmanager.eu-central-1.amazonaws.com"
    cors_urls: List[HttpUrl] = []

    display_traceback: bool = False
    debug: bool = False
    testing_mode: bool = False

    @classmethod
    def get_testing_mode(cls) -> bool:
        return MuseumTestingFlags.get().mode

    root_path: Optional[pathlib.Path] = None

    allow_origin_regex: re.Pattern = re.compile(
        r"^(http://(.*\.)?localhost:\d+|https://.*\.museum\.(dev|io))/?$"
    )

    @model_validator(mode="before")
    @classmethod
    def compatible_testing_mode(cls, values: Dict[str, Any]):
        testing_mode = cls.get_testing_mode()
        namespace = values.get("namespace")
        if testing_mode and any(k in namespace for k in ("staging", "production")):
            raise ValueError(
                "`testing_mode` cannot be true when "
                + "('staging', 'production') in `NAMESPACE`"
            )
        return values

    @property
    def superuser_email(self) -> str:
        return MuseumSuperuserFlags.get().email


class BulkSettings(Flags):
    _museumflags_key = "bulk_settings"
    fast_save: bool = False

    @classmethod
    def use_fast_save(cls, creations: List):
        return cls.get().fast_save or len(creations) >= 1000
