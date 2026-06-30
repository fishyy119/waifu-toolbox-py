from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass
class FakeProgressReporter:
    total: int
    desc: str
    updates: list[int] = field(default_factory=lambda: [])
    postfixes: list[str] = field(default_factory=lambda: [])
    closed: bool = False

    def update(self, n: int = 1) -> None:
        self.updates.append(n)

    def set_postfix(self, text: str) -> None:
        self.postfixes.append(text)

    def close(self) -> None:
        self.closed = True


def create_image(
    path: Path,
    *,
    size: tuple[int, int] = (16, 16),
    color: Any = (255, 0, 0),
    mode: str = "RGB",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new(mode, size, color).save(path)
    return path


def create_text_file(path: Path, content: str = "text") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
