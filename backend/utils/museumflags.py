import json
import logging
import os
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple, Type, TypeVar

import pydantic
import yaml
from pydantic import model_validator
from pydantic.fields import Field, FieldInfo
from pydantic.main import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

logger = logging.getLogger(__name__)

_SECRETS_DIR = ".secrets"


def Secret(secret: str) -> pydantic.Field:
    return Field(
        default_factory=lambda: os.environ.get(secret, ""),
        description=f"Secret '{secret}'",
    )


class _Meta(type(BaseSettings)):
    def __new__(cls, name, bases, dct):
        if key := dct.get("_museumflags_key"):
            dct.setdefault("model_config", {})["env_prefix"] = f"{key}_"
        return super().__new__(cls, name, bases, dct)


class _Museumflags(BaseSettings, metaclass=_Meta):
    _museumflags_key = "museumflags"
    file: Optional[Path] = None
    contents: Optional[str] = None
    contents_json: Optional[str] = None
    target: Optional[str] = None
    use_env_settings: bool = True
    verbose: bool = False

    @model_validator(mode="before")
    @classmethod
    def more_than_1_set(cls, values: Dict[str, Any]):
        check_values = {
            k: values[k] for k in {"file", "contents", "contents_json"} if k in values
        }
        if len([x for x in check_values.values() if x]) > 1:
            raise Exception(f"Only 1 configuration may be specified: {check_values}")
        return values

    @property
    def spec(self) -> Dict[str, Any]:
        root = {}
        if self.contents:
            root = yaml.safe_load(self.contents)
        elif self.contents_json:
            root = json.loads(self.contents_json)
        elif self.file and (path := Path(self.file)).is_file():
            root = yaml.safe_load(path.read_text())

        targets = root.pop("targets", {})

        def merge(a, b):
            return {
                **a,
                **{
                    k: {**a.get(k, {}), **v} if isinstance(v, dict) else v
                    for k, v in b.items()
                },
            }

        def get_target(t):
            if not t:
                return {}
            target = targets.get(t, {})
            return merge(get_target(target.pop("extends", None)), target)

        return merge(root, get_target(self.target))


_T = TypeVar("_T", bound="Flags")


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> Tuple[Any, str, bool]:
        self.config.get("env_file_encoding")
        spec = _Museumflags().spec
        museumflags_key = self.settings_cls._museumflags_key.get_default()
        flags = spec.get(museumflags_key if museumflags_key else "unkeyed", {})
        field_value = flags.get(field_name)
        return field_value, field_name, False

    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, value_is_complex = self.get_field_value(
                field, field_name
            )
            field_value = self.prepare_field_value(
                field_name, field, field_value, value_is_complex
            )
            if field_value is not None:
                d[field_key] = field_value

        return d


def fix(x):
    x.__doc__ = f"""{x.__doc__ or Flags.__doc__ or ''}

`museumflags_key` = *`{x._museumflags_key.default}`*
"""
    return x


class Flags(BaseSettings, metaclass=_Meta):
    """Museumflags settings."""

    model_config = SettingsConfigDict(validate_default=False, env_file_encoding="utf-8")
    _default: _T = None
    _museumflags_key: str = None
    _registry: Optional[Set[_T]] = set()

    def _museumflags_log(self):
        if logging.root.level > logging.INFO:
            logging.basicConfig(level=logging.INFO)
        logger.info(f"""

        {self.__class__.__name__}

{self.model_dump_json(indent=2)}

""")

    @classmethod
    def __pydantic_init_subclass__(cls):
        if cls.__base__._registry and hasattr(cls.__base__._registry, "get_default"):
            cls.__base__._registry = set()
        if cls._museumflags_key:
            for c in cls.__base__._registry:
                if c._museumflags_key == cls._museumflags_key:
                    raise Exception(
                        f"Cannot register Museumflags {cls}."
                        + f"_museumflags_key {cls._museumflags_key}"
                        + f" already registered by {c}"
                    )
        cls.__base__._registry.add(cls)

    @classmethod
    def full_schema(cls) -> str:
        return pydantic.create_model(
            "Museumflags",
            **{x.__name__: (fix(x), ...) for x in cls._registry},
        ).model_json_schema()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        base = (
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
            init_settings,
        )
        if _Museumflags().use_env_settings:
            return (env_settings, *base)
        return base

    @classmethod
    def get(cls: Type[_T]) -> _T:
        if cls is Flags:
            raise Exception("cannot get base Flags class, please subclass")

        if cls._default and not hasattr(cls._default, "get_default"):
            return cls._default
        else:
            warnings.simplefilter("ignore", UserWarning)
            cls._default = cls()
        if _Museumflags().verbose:
            cls._default._museumflags_log()
        return cls._default

    def export_to_env(self):
        os.environ.update(self.env_vars_dict(secrets=True))

    @property
    def as_env_vars(self) -> Dict[str, str]:
        return self.env_vars_dict(secrets=False)

    def env_vars_dict(self, secrets: bool = False) -> Dict[str, str]:
        return {
            "_".join(
                filter(
                    bool,
                    (self._museumflags_key, k),
                )
            ).upper(): (
                int(v)
                if isinstance(v, bool)
                else (
                    json.dumps(v) if isinstance(v, (dict, list, BaseModel)) else str(v)
                )
            )
            for k, v in self.model_dump(
                exclude_defaults=True,
                exclude_none=True,
                exclude_unset=not secrets,
            ).items()
        }
