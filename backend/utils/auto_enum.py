import enum
from enum import Enum, unique

auto = enum.auto


@unique
class AutoEnum(str, Enum):
    def _generate_next_value_(name: str, *args, **kwargs):
        return name
