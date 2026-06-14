import json
from itertools import count
from pathlib import Path
from typing import List, Literal, TypedDict
from urllib.parse import quote

from nicegui import app, ui


class ImageItem(TypedDict):
    relative_path: str
    label: str


class _ViewerState(TypedDict):
    page: int


_VIEWER_IDS = count()


def serve_repo_images(repo_name: str, repo_path: Path) -> str:
    url_path = f"/repo-images/{quote(repo_name, safe='')}"
    app.add_media_files(url_path, repo_path)
    return url_path


def show_lightbox(src: str) -> None:
    ui.run_javascript(f"window.WaifuImageViewer?.showLightbox({json.dumps(src)})")


def image_viewer(
    images: List[ImageItem],
    url_prefix: str,
    page_size: int = 50,
    columns: int = 0,
    mode: Literal["grid", "masonry"] = "grid",
):
    total = len(images)
    state: _ViewerState = {"page": 0}
    viewer_id = next(_VIEWER_IDS)

    with ui.column().classes("w-full gap-4"):
        with ui.row().classes("items-center gap-4"):
            info_label = ui.label().classes("text-xs text-muted")
            ui.space()

        content = ui.element("div").classes("w-full")
        nav_row = ui.row().classes("items-center justify-center gap-2")

    def render_page() -> None:
        content.clear()
        start = state["page"] * page_size
        end = min(start + page_size, total)

        info_label.text = f"共 {total} 张图片" + (f"  第 {start + 1}-{end} 张" if total > page_size else "")

        page_images = images[start:end]
        srcs = [f"{url_prefix}/{quote(img['relative_path'], safe='/')}" for img in page_images]

        with content:
            if mode == "masonry":
                _render_masonry(srcs)
                ui.run_javascript(f"window.WaifuImageViewer?.layoutMasonry({json.dumps(f'.masonry-grid-{viewer_id}')})")
            else:
                _render_grid(srcs)

        _render_nav(nav_row, state, total, page_size)

    def _render_grid(srcs: list[str]) -> None:
        if columns > 0:
            col_css = f"repeat({columns}, 1fr)"
        else:
            col_css = "repeat(auto-fill, minmax(160px, 1fr))"
        grid = ui.element("div").classes("w-full grid gap-2").style(f"grid-template-columns: {col_css};")
        with grid:
            for src in srcs:
                img = ui.image(src).classes("w-full aspect-square object-cover rounded cursor-zoom-in")
                img.on("click", lambda _, s=src: show_lightbox(s))

    def _render_masonry(srcs: list[str]) -> None:
        if columns > 0:
            grid_style = f"grid-template-columns: repeat({columns}, minmax(0, 1fr));"
        else:
            grid_style = "grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));"
        masonry = ui.element("div").classes(f"masonry-grid masonry-grid-{viewer_id}").style(grid_style)
        with masonry:
            for src in srcs:
                with ui.element("div").classes("masonry-item"):
                    img = ui.image(src)
                    img.on("click", lambda _, s=src: show_lightbox(s))

    def go_page(p: int) -> None:
        max_page = (total - 1) // page_size if total else 0
        state["page"] = max(0, min(p, max_page))
        render_page()

    def _render_nav(row: ui.row, st: _ViewerState, tot: int, ps: int) -> None:
        row.clear()
        if tot <= ps:
            return
        max_page = (tot - 1) // ps
        page = st["page"]
        with row:
            ui.button(
                icon="navigate_before",
                on_click=lambda: go_page(page - 1),
            ).props(
                "flat dense"
            ).set_enabled(page > 0)
            ui.label(f"{page + 1} / {max_page + 1}")
            ui.button(
                icon="navigate_next",
                on_click=lambda: go_page(page + 1),
            ).props(
                "flat dense"
            ).set_enabled(page < max_page)

    render_page()
