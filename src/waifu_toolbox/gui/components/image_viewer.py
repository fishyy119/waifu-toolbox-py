import json
from itertools import count
from pathlib import Path
from typing import Literal, TypedDict
from urllib.parse import quote

from nicegui import app, ui
from nicegui.binding import bindable_dataclass


class ImageItem(TypedDict):
    relative_path: str
    label: str


@bindable_dataclass
class _ViewerState:
    page: int


_VIEWER_IDS = count()


def serve_repo_images(repo_name: str, repo_path: Path) -> str:
    url_path = f"/repo-images/{quote(repo_name, safe='')}"
    app.add_media_files(url_path, repo_path)
    return url_path


def show_lightbox(src: str) -> None:
    ui.run_javascript(f"window.WaifuImageViewer?.showLightbox({json.dumps(src)})")


def _quote_relative_url_path(relative_path: str) -> str:
    parts = [part for part in relative_path.replace("\\", "/").strip("/").split("/") if part and part != "."]
    return "/".join(quote(part, safe="") for part in parts)


def image_viewer(
    images: list[ImageItem],
    url_prefix: str,
    page_size: int = 50,
    columns: int = 5,
    mode: Literal["grid", "masonry"] = "grid",
) -> None:
    total = len(images)
    max_page = (total - 1) // page_size if total else 0
    state = _ViewerState(page=0)
    viewer_id = next(_VIEWER_IDS)
    column_count = max(1, columns)

    def _page_bounds(page: int) -> tuple[int, int]:
        start = page * page_size
        end = min(start + page_size, total)
        return start, end

    def _info_text(page: int) -> str:
        start, end = _page_bounds(page)
        text = f"共 {total} 张图片"
        if total > page_size:
            text += f"  第 {start + 1}-{end} 张"
        return text

    def _page_srcs(page: int) -> list[str]:
        start, end = _page_bounds(page)
        page_images = images[start:end]
        return [f"{url_prefix}/{_quote_relative_url_path(img['relative_path'])}" for img in page_images]

    @ui.refreshable
    def render_content() -> None:
        srcs = _page_srcs(state.page)
        with ui.element("div").classes("w-full"):
            if mode == "masonry":
                _render_masonry(srcs, column_count, viewer_id)
                ui.run_javascript(f"window.WaifuImageViewer?.layoutMasonry({json.dumps(f'.masonry-grid-{viewer_id}')})")
            else:
                _render_grid(srcs, column_count)

    def _render_grid(srcs: list[str], grid_columns: int) -> None:
        col_css = f"repeat({grid_columns}, 1fr)"
        grid = ui.element("div").classes("w-full grid gap-2").style(f"grid-template-columns: {col_css};")
        with grid:
            for src in srcs:
                img = ui.image(src).classes("w-full aspect-square object-cover rounded cursor-zoom-in")
                img.on("click", lambda _, s=src: show_lightbox(s))

    def _render_masonry(srcs: list[str], grid_columns: int, current_viewer_id: int) -> None:
        grid_style = f"--masonry-columns: {grid_columns};"
        masonry = ui.element("div").classes(f"masonry-grid masonry-grid-{current_viewer_id}").style(grid_style)
        with masonry:
            for src in srcs:
                with ui.element("div").classes("masonry-item"):
                    # 完全自绘，不用框架封装后的 img
                    img = ui.element("img").props(f"src={json.dumps(src)} loading=eager decoding=async")
                    img.on("click", lambda _, s=src: show_lightbox(s))

    def go_page(p: int) -> None:
        target_page = max(0, min(p, max_page))
        if target_page == state.page:
            return
        state.page = target_page
        render_content.refresh()

    with ui.column().classes("w-full gap-4"):
        with ui.row().classes("items-center gap-4"):
            ui.label().classes("text-xs text-muted").bind_text_from(state, "page", backward=_info_text)
            ui.space()

        if total > page_size:
            with ui.row().classes("items-center justify-center gap-2"):
                ui.button(
                    icon="navigate_before",
                    on_click=lambda: go_page(state.page - 1),
                ).props(
                    "flat dense"
                ).bind_enabled_from(state, "page", backward=lambda page: page > 0)
                ui.label().bind_text_from(state, "page", backward=lambda page: f"{page + 1} / {max_page + 1}")
                ui.button(
                    icon="navigate_next",
                    on_click=lambda: go_page(state.page + 1),
                ).props(
                    "flat dense"
                ).bind_enabled_from(state, "page", backward=lambda page: page < max_page)

        render_content()
