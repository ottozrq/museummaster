import dataclasses
import hashlib
import json
import re
from datetime import timedelta
from pathlib import Path, PosixPath
from typing import Any, Dict, Set, Type, Union

import requests
import yaml
from pydantic import BaseModel, ConfigDict, Field, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from utils import museumflags


class Link(PosixPath):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls, handler(Path))


class AutoLink(Link):
    pass


@dataclasses.dataclass(frozen=True)
class ModelResponse:
    model: "Model"
    response: requests.Response

    @property
    def time(self) -> timedelta:
        return self.response.elapsed

    @property
    def url(self) -> str:
        return self.response.request.path_url


class MuseumModelsFlags(museumflags.Flags):
    _museumflags_key = "museummodels"
    extra: str = "ignore"


class ModelNoConfig(BaseModel):
    @classmethod
    def parse_lambda_event(cls, event: Union[str, Dict]):
        if isinstance(event, str):
            event = json.loads(event)
        return cls.model_validate(event)

    @classmethod
    def from_response(cls, response: requests.Response):
        return cls.model_validate(response.json())

    def json_dict(self, sorted_deep=False, *args, **kwargs) -> Dict[str, Any]:
        def sorted_deep_(d):
            # https://stackoverflow.com/questions/56305009/how-to-sort-all-lists-in-a-deeply-nested-dictionary-in-python
            def make_tuple(v):
                return (*v,) if isinstance(v, (list, dict)) else (v,)

            if isinstance(d, list):
                # if first element is a dict, sort by key
                if len(d) > 1 and isinstance(d[0], dict):
                    if "grouping" in d[0]:
                        key = "grouping"
                    elif "uri" in d[0]:
                        key = "uri"
                    else:
                        key = next(iter(d[0]))
                    return sorted(map(sorted_deep_, d), key=lambda x: x[key])
                return sorted(map(sorted_deep_, d), key=make_tuple)
            if isinstance(d, dict):
                return {k: sorted_deep_(d[k]) for k in sorted(d)}
            return d

        json_dict = json.loads(self.model_dump_json(by_alias=True, *args, **kwargs))

        if sorted_deep:
            return sorted_deep_(json_dict)

        return json_dict

    @property
    def __hash__(self):
        # https://stackoverflow.com/questions/5884066/hashing-a-dictionary
        # TODO : https://en.wikipedia.org/wiki/Secure_Hash_Algorithm_(disambiguation)
        # A drawback of cryptographic hash algorithms such as MD5 and SHA is that they take considerably longer to execute than Rabin's fingerprint algorithm.
        # For now, they take up to 10ms max, so it's not a problem.
        return hashlib.md5(
            json.dumps(self.json_dict(sorted_deep=True), sort_keys=True).encode(),
            usedforsecurity=False,
        ).hexdigest()

    def database_dict(self) -> Dict[str, Any]:
        return self.json_dict(
            exclude_unset=True,
            exclude_defaults=True,
            exclude_none=True,
        )

    @classmethod
    def fields(cls) -> Dict[str, Field]:
        return cls.model_fields

    def patch_equals(self, other: "Model") -> bool:
        return not self.patched_fields(other)

    def patched_fields(self, other: "Model") -> Set[str]:
        return {
            field
            for field in set(self.fields()).intersection(other.fields())
            if getattr(self, field) not in (None, getattr(other, field, None))
        }

    def patch(self, other: "Model", klass: Type["Model"]) -> "Model":
        return klass(
            **{
                field: getattr(self, field, None) or getattr(other, field)
                for field in klass.fields()
            }
        )

    @classmethod
    def from_yaml(cls, path: Path):
        return cls.model_validate(yaml.safe_load(path.read_text()))

    @staticmethod
    def validated_uri(uri: Union[str, PosixPath], fmt: str, exception=None):
        if uri:
            if isinstance(uri, PosixPath):
                uri_str = uri.as_posix()
            else:
                uri_str = uri
            if not re.match(re.compile(fmt), uri_str):
                raise exception or ValueError(f"Invalid uri: {uri}")
        return uri


class Model(ModelNoConfig):
    model_config = ConfigDict(extra=MuseumModelsFlags.get().extra)
