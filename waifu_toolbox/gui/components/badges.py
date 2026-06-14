from typing import NamedTuple

from nicegui import ui


def badge(text: str, variant: str = "") -> None:
    cls = f"badge {variant}".rstrip() if variant else "badge"
    ui.html(f'<span class="{cls}">{text}</span>')


def feature_badge(name: str, count: int, total: int) -> None:
    if total == 0:
        variant = ""
    elif count == total:
        variant = "badge-success"
    elif count > 0:
        variant = "badge-warning"
    else:
        variant = "badge-destructive"
    badge(f"{name} {count}/{total}", variant)


class _StatusEntry(NamedTuple):
    text: str
    variant: str


_STATUS_MAP: dict[str, _StatusEntry] = {
    "pending": _StatusEntry("等待中", ""),
    "running": _StatusEntry("运行中", "badge-warning"),
    "completed": _StatusEntry("已完成", "badge-success"),
    "failed": _StatusEntry("失败", "badge-destructive"),
}


def status_badge(status: str) -> None:
    entry = _STATUS_MAP.get(status, _StatusEntry(status, ""))
    badge(entry.text, entry.variant)
