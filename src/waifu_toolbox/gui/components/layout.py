from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from nicegui import ui
from nicegui.binding import bindable_dataclass


class Theme(TypedDict):
    primary: str
    foreground: str
    muted_foreground: str
    border: str


THEME: Theme = {
    "primary": "#18181b",
    "foreground": "#09090b",
    "muted_foreground": "#71717a",
    "border": "#e4e4e7",
}

_ASSETS_DIR = Path(__file__).parent.parent / "assets"
SHADCN_CSS = (_ASSETS_DIR / "shadcn.css").read_text(encoding="utf-8")
IMAGE_VIEWER_CSS = (_ASSETS_DIR / "image_viewer.css").read_text(encoding="utf-8")

_shared_assets_ready = False


_NAV_ITEMS = [
    ("仓库列表", "/"),
    ("分类", "/classify"),
    ("排序", "/sort"),
    ("格式转换", "/convert"),
    ("相似搜索", "/search"),
]

_NAV_SECONDARY = [
    ("任务队列", "/tasks"),
    ("设置", "/settings"),
]


@dataclass(frozen=True)
class DrawerPanel:
    key: str
    label: str
    render: Callable[[], None]
    icon: str = "menu"  # 在顶栏展示的切换图标


@dataclass(frozen=True)
class PageLayoutOptions:
    drawer_panels: Sequence[DrawerPanel] = ()  # 需要附加的其他侧边栏面板，默认会包含一个页面导航面板
    default_drawer_panel: str | None = None  # 默认选中面板名
    include_default_navigation: bool = True  # 保留默认面板


@bindable_dataclass
class DrawerState:
    panel: str


def ensure_shared_assets() -> None:
    global _shared_assets_ready
    if _shared_assets_ready:
        return
    ui.add_css(SHADCN_CSS, shared=True)
    ui.add_css(IMAGE_VIEWER_CSS, shared=True)
    ui.add_head_html('<script src="/assets/image_viewer.js"></script>', shared=True)
    _shared_assets_ready = True


def page_layout(path: str, *, options: PageLayoutOptions | None = None) -> None:
    ensure_shared_assets()
    ui.dark_mode(False)

    config = options or PageLayoutOptions()
    panels = list(config.drawer_panels)

    # 如果需要默认的导航页面板，加入列表中
    if config.include_default_navigation or not panels:
        panels.append(
            DrawerPanel(key="navigation", label="页面导航", render=lambda: _render_navigation(path), icon="dashboard")
        )

    panel_map = {panel.key: panel for panel in panels}
    default_panel = config.default_drawer_panel if config.default_drawer_panel in panel_map else panels[0].key
    drawer_state = DrawerState(panel=default_panel)

    left_drawer = ui.left_drawer(value=True).style(
        "background: var(--background); border-right: 1px solid var(--border);" "padding: 1rem 0.75rem;"
    )

    with left_drawer:
        with ui.column().classes("w-full gap-2 mt-1"):

            @ui.refreshable
            def render_drawer_panel() -> None:
                panel_map[drawer_state.panel].render()

            render_drawer_panel()

    def _toggle_drawer_panel() -> None:
        current_index = next((index for index, panel in enumerate(panels) if panel.key == drawer_state.panel), 0)
        next_panel_key = panels[(current_index + 1) % len(panels)].key

        if next_panel_key not in panel_map or next_panel_key == drawer_state.panel:
            return

        drawer_state.panel = next_panel_key
        render_drawer_panel.refresh()

    with (
        ui.header()
        .classes("items-center")
        .style(
            "background: var(--background); color: var(--foreground);"
            "border-bottom: 1px solid var(--border); box-shadow: none;"
        )
    ):
        # 切换侧栏收起展开
        ui.button(icon="menu", on_click=left_drawer.toggle).props("flat dense color=dark")

        # 切换侧栏内容
        if len(panels) > 1:
            panel_toggle_button = ui.button(on_click=_toggle_drawer_panel).props("flat dense color=dark")
            panel_toggle_button.bind_icon_from(drawer_state, "panel", backward=lambda key: panel_map[key].icon)
            with panel_toggle_button:
                ui.tooltip().bind_text_from(drawer_state, "panel", backward=lambda key: panel_map[key].label)

        ui.label("Waifu Toolbox").classes("text-base font-semibold tracking-tight px-3")


def _render_navigation(path: str) -> None:
    with ui.column().classes("w-full gap-0.5"):
        for label, href in _NAV_ITEMS:
            _nav_link(label, href, path)

        ui.separator().classes("my-2")

        for label, href in _NAV_SECONDARY:
            _nav_link(label, href, path)


def _nav_link(label: str, href: str, current_path: str) -> None:
    if href == "/":
        active = current_path == "/" or current_path.startswith("/repo")
    else:
        active = current_path.startswith(href)
    cls = "nav-link no-underline"
    if active:
        cls += " nav-link-active"
    ui.link(label, href).classes(cls)
