from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

from nicegui import ui

from ..context import DrawerPanel, GuiContext


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


def ensure_shared_assets() -> None:
    global _shared_assets_ready
    if _shared_assets_ready:
        return
    ui.add_css(SHADCN_CSS, shared=True)
    ui.add_css(IMAGE_VIEWER_CSS, shared=True)
    ui.add_head_html('<script src="/assets/image_viewer.js"></script>', shared=True)
    _shared_assets_ready = True


def render_shell(ctx: GuiContext, routes: dict[str, Callable[..., Any]]) -> None:
    ensure_shared_assets()
    ui.dark_mode(False)

    navigation_panel = DrawerPanel(
        key="navigation",
        label="页面导航",
        render=lambda: _render_navigation(ctx.shell_state.current_path),
        icon="dashboard",
    )
    ctx.set_navigation_panel(navigation_panel)

    left_drawer = ui.left_drawer(value=True).style(
        "background: var(--background); border-right: 1px solid var(--border); padding: 1rem 0.75rem;"
    )

    with left_drawer, ui.column().classes("w-full gap-2 mt-1"):

        @ui.refreshable
        def render_drawer_panel() -> None:
            panel = ctx.current_panel
            if panel is None:
                ui.label("暂无可用面板").classes("text-sm text-muted")
                return
            panel.render()

        render_drawer_panel()

    @ui.refreshable
    def render_header_controls() -> None:
        panels = ctx.drawer_panels
        if len(panels) <= 1:
            return
        panel_map = {panel.key: panel for panel in panels}
        current_key = ctx.shell_state.panel
        current_panel = panel_map.get(current_key, panels[0])
        ui.button(icon=current_panel.icon, on_click=ctx.toggle_drawer_panel).props("flat dense color=dark")

    def refresh_drawer() -> None:
        render_drawer_panel.refresh()

    def refresh_header() -> None:
        render_header_controls.refresh()

    ctx.register_shell_callbacks(
        refresh_drawer=refresh_drawer,
        refresh_header=refresh_header,
    )

    with (
        ui.header()
        .classes("items-center")
        .style(
            "background: var(--background); color: var(--foreground);"
            "border-bottom: 1px solid var(--border); box-shadow: none;"
        )
    ):
        ui.button(icon="menu", on_click=left_drawer.toggle).props("flat dense color=dark")
        render_header_controls()
        ui.label("Waifu Toolbox").classes("text-base font-semibold tracking-tight px-3")

    with ui.column().classes("w-full"):
        ui.sub_pages(routes=routes, data={"ctx": ctx}).classes("w-full")


def _render_navigation(path: str) -> None:
    with ui.column().classes("w-full gap-0.5"):
        for label, href in _NAV_ITEMS:
            _nav_link(label, href, path)

        ui.separator().classes("my-2")

        for label, href in _NAV_SECONDARY:
            _nav_link(label, href, path)


def _nav_link(label: str, href: str, current_path: str) -> None:
    active = current_path == "/" or current_path.startswith("/repo") if href == "/" else current_path.startswith(href)

    cls = "nav-link"
    if active:
        cls += " nav-link-active"

    ui.button(
        label,
        on_click=lambda _, target=href: ui.navigate.to(target),
    ).props(
        "flat no-caps"
    ).classes(f"{cls} justify-start")
