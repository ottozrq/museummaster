from dataclasses import dataclass
from pathlib import Path
from typing import Any, Type, TypeVar

import requests

from utils.museummodels import Model

ModelT = TypeVar("ModelT", bound=Model)


@dataclass(frozen=True)
class WrappedResponse:
    response: requests.Response
    _url: Path

    def wrap(self, model: Type[ModelT]) -> ModelT:
        return model.model_validate(self.json())

    def __getattr__(self, name: str) -> Any:
        return getattr(self.response, name)
