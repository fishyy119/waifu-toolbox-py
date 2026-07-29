"""
全局 UI 偏好存储。

运行时使用 bindable_dataclass 承载，可安全配合 NiceGUI bind_value 绑定。
启动时从 JSON 文件恢复，关闭时写回磁盘。
"""

from dataclasses import asdict, dataclass, field
from typing import ClassVar, Literal

from nicegui.binding import bindable_dataclass
from pydantic import ConfigDict, TypeAdapter, ValidationError

from ...paths import PATHS


@dataclass
class _UIPreferencesSchema:
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    selected_dirs: dict[str, str] = field(default_factory=lambda: {})
    viewer_columns: int = 5
    viewer_page_size: int = 50
    viewer_view_mode: Literal["grid", "masonry"] = "grid"


# bindable_dataclass 通过数据描述符将定义字段的存储键名映射到下划线开头的私有字段，
# 而 typeadpter 导出的 dataclass 会跳过这步，导致运行时取值失败
# 因此定义了两个 dataclass，先读取出普通 dataclass后，再正常初始化 bindable_dataclass
@bindable_dataclass
class _UIPreferences(_UIPreferencesSchema):
    pass


_PREFERENCES_PATH = PATHS.waifu_home / "gui_preferences.json"
_PREFERENCES_ADAPTER = TypeAdapter(_UIPreferencesSchema)


def _make_preferences() -> _UIPreferences:
    """从磁盘恢复偏好值。"""
    try:
        schema = _PREFERENCES_ADAPTER.validate_json(
            _PREFERENCES_PATH.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError, ValueError):
        schema = _UIPreferencesSchema()

    return _UIPreferences(**asdict(schema))


prefs = _make_preferences()


def save() -> None:
    """关闭时将当前偏好值写入磁盘。"""
    _PREFERENCES_PATH.write_bytes(
        _PREFERENCES_ADAPTER.dump_json(
            prefs,
            indent=2,
        )
    )
