from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")


@dataclass
class Result[T]:
    ok: bool
    message: str
    data: T | None = None
