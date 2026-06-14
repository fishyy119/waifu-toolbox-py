from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class Result(Generic[T]):
    ok: bool
    message: str
    data: T | None = None
