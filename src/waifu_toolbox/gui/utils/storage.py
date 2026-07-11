"""
全局 UI 偏好存储。

运行时使用 bindable_dataclass 承载，可安全配合 NiceGUI bind_value 绑定。
启动时从 app.storage.general 恢复，关闭时写回 general 持久化到磁盘。
"""

import json
from dataclasses import dataclass, field
from typing import Any, Callable, NamedTuple

from nicegui import app
from nicegui.binding import bindable_dataclass


@bindable_dataclass
@dataclass
class _UIPreferences:
    selected_dirs: dict[str, str] = field(default_factory=lambda: {})

    viewer_columns: int = 5
    viewer_page_size: int = 50
    viewer_view_mode: str = "grid"


class PreferenceSpec(NamedTuple):
    attr: str
    default: object
    encode: Callable[[Any], Any]
    decode: Callable[[Any], Any]


PREFERENCE_SPECS: tuple[PreferenceSpec, ...] = (
    PreferenceSpec(
        "viewer_columns",
        5,
        int,
        int,
    ),
    PreferenceSpec(
        "viewer_page_size",
        50,
        int,
        int,
    ),
    PreferenceSpec(
        "viewer_view_mode",
        "grid",
        str,
        str,
    ),
    PreferenceSpec(
        "selected_dirs",
        {},
        json.dumps,
        json.loads,
    ),
)

prefs = _UIPreferences()


# TODO: 使用 storage API 的意义实际上已经不大了，完全可以重新实现一个简单的 JSON 读写，外加使用 Pydantic 验证
def load() -> None:
    """启动时从 general 恢复偏好值。"""
    for attr, default, _, decode in PREFERENCE_SPECS:
        raw = app.storage.general.get(attr)  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        setattr(prefs, attr, decode(raw) if raw is not None else default)


def save() -> None:
    """关闭时将当前偏好值写入 general 持久化。"""
    for attr, _, encode, _ in PREFERENCE_SPECS:
        app.storage.general[attr] = encode(getattr(prefs, attr))
