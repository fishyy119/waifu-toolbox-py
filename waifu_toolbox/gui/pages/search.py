from pathlib import Path
from urllib.parse import quote

from nicegui import app, ui

from ...db.operations import list_repos, search_similar
from ..components.file_picker import file_picker
from ..components.image_viewer import show_lightbox
from ..components.layout import page_layout
from ..services.task_manager import task_manager

_IMAGE_FILETYPES = [("图片", "*.png *.jpg *.jpeg *.webp *.bmp *.gif")]


def render():
    page_layout("/search")

    with ui.column().classes("w-full p-6 gap-4 max-w-5xl"):
        ui.label("相似图片搜索").classes("text-2xl font-semibold tracking-tight")
        ui.label("基于 DreamSim 特征在仓库中查找最相似的图片").classes("text-sm text-muted")

        repos = list_repos()
        repo_names = [r.name for r in repos]

        with ui.card().classes("w-full"):
            repo_select = ui.select(
                label="搜索仓库",
                options=repo_names,
                value=repo_names[0] if repo_names else None,
            ).classes("w-64")

            query_input = file_picker(label="查询图片", filetypes=_IMAGE_FILETYPES)

            with ui.row().classes("items-center gap-4"):
                top_k = ui.number(label="结果数量", value=10, min=1, max=50, step=1).classes("w-32")
                skip_update = ui.checkbox("跳过自动更新索引", value=True)

        results_container = ui.column().classes("w-full")

        async def do_search():
            repo = repo_select.value
            query = query_input.value
            if not repo:
                ui.notify("请选择仓库", type="negative")
                return
            if not query or not Path(query).exists():
                ui.notify("请输入有效的图片路径", type="negative")
                return

            results_container.clear()
            with results_container:
                ui.label("搜索中...").classes("text-sm text-muted")

            result = await task_manager.run_result(
                f"相似搜索: {repo}",
                search_similar,
                repo,
                Path(query),
                int(top_k.value or 10),
                skip_update=bool(skip_update.value),
            )

            results_container.clear()
            if not result.ok or result.data is None:
                ui.notify(result.message, type="negative")
                return
            results = result.data

            with results_container:
                ui.label(f"Top {len(results)} 结果").classes("text-sm font-semibold")
                grid = (
                    ui.element("div")
                    .classes("w-full grid gap-3")
                    .style("grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));")
                )
                with grid:
                    for r in results:
                        img_path = Path(r.path)
                        with ui.card().classes("p-1 overflow-hidden").tight():
                            if img_path.exists():
                                src = _serve_single_image(img_path)
                                img = ui.image(src).classes("w-full aspect-square object-cover cursor-zoom-in")
                                img.on("click", lambda _, s=src: show_lightbox(s))
                            else:
                                ui.label("文件不存在").classes("text-xs text-destructive-fg p-4")
                            with ui.column().classes("px-2 py-1.5 gap-0"):
                                ui.label(r.label).classes("text-xs font-semibold")
                                ui.label(f"相似度: {r.similarity:.4f}").classes("text-xs text-muted")
                                ui.label(img_path.as_posix()).classes(
                                    "text-xs text-muted leading-snug whitespace-normal break-all"
                                )

        ui.button("搜索", icon="search", on_click=do_search)


_served_dirs: dict[str, str] = {}


def _serve_single_image(img_path: Path) -> str:
    parent = img_path.parent
    key = str(parent)
    if key not in _served_dirs:
        url_path = f"/search-images/{len(_served_dirs)}"
        app.add_media_files(url_path, parent)
        _served_dirs[key] = url_path
    return f"{_served_dirs[key]}/{quote(img_path.name, safe='')}"
