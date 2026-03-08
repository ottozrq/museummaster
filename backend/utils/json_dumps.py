import json
import uuid
from datetime import datetime, time
from pathlib import Path

from pydantic import BaseModel
from pydantic_core import Url


def jsonify(value):
    if isinstance(value, BaseModel):
        return json.loads(value.model_dump_json())
    if isinstance(value, (datetime, time)):
        return value.isoformat()
    if isinstance(value, (uuid.UUID, Path, Url)):
        return str(value)
    return value


def museum_json_dumps(obj) -> str:
    """Serializes object to JSON, accounting for common Museum types."""
    return json.dumps(obj, default=jsonify)
