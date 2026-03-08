import logging
from typing import Dict

from fastapi import Depends, HTTPException, Response, status

import depends as d
import models as m
import sql_models as sm
from app import app
from utils.flags import MuseumFlags
from utils.utils import MuseumDb

logger = logging.getLogger(__name__)

schema_show_all = MuseumFlags.get().debug

TAG = m.OpenAPITag


def pruned_dict(_prune_all: bool = False, **kwargs) -> Dict:
    return {} if _prune_all else {k: v for k, v in kwargs.items() if v}


__all__ = [
    "app",
    "d",
    "Depends",
    "m",
    "sm",
    "schema_show_all",
    "TAG",
    "logger",
    "MuseumDb",
    "Response",
    "status",
    "HTTPException",
]
