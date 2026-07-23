from pathlib import Path
from urllib.parse import quote

from nicegui import PageArguments, app, ui

from ...db.operations import list_repos, search_similar
from ..components.file_picker import file_picker
from ..components.image_viewer import show_lightbox
from ..context import GuiContext, SearchResultEntry

_IMAGE_FILETYPES = [("图片", "*.png *.jpg *.jpeg *.webp *.bmp *.gif")]


def render(ctx: GuiContext, page_args: PageArguments) -> None:
    ctx.activate_route(page_args.path)

    with ui.column().classes("w-full p-6 gap-4 max-w-5xl"):
        ui.label("相似图片搜索").classes("text-2xl font-semibold tracking-tight")
        ui.label("基于 DreamSim 特征在仓库中查找最相似的图片").classes("text-sm text-muted")

        repos = list_repos()
        repo_names = [r.name for r in repos]
        state = ctx.search_state
        if repo_names and state.repo_name not in repo_names:
            state.repo_name = repo_names[0]
        if not repo_names:
            state.repo_name = ""

        with ui.card().classes("w-full"):
            ui.select(
                label="搜索仓库",
                options=repo_names,
                value=state.repo_name or None,
            ).classes("w-64").bind_value(state, "repo_name")

            file_picker(label="查询图片", filetypes=_IMAGE_FILETYPES).bind_value(state, "query_path")

            with ui.row().classes("items-center gap-4"):
                ui.number(label="结果数量", min=1, max=50, step=1).classes("w-32").bind_value(state, "top_k")
                ui.checkbox("跳过自动更新索引").bind_value(state, "skip_update")

        @ui.refreshable
        def render_results() -> None:
            if state.loading:
                ui.label("搜索中...").classes("text-sm text-muted")
                return

            if state.error:
                ui.label(state.error).classes("text-sm text-destructive-fg")
                return

            if not ctx.search_results:
                ui.label("暂无搜索结果").classes("text-sm text-muted")
                return

            ui.label(f"Top {len(ctx.search_results)} 结果").classes("text-sm font-semibold")
            grid = (
                ui.element("div")
                .classes("w-full grid gap-3")
                .style("grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));")
            )
            with grid:
                for result in ctx.search_results:
                    img_path = Path(result.path)
                    with ui.card().classes("p-1 overflow-hidden").tight():
                        if img_path.exists():
                            src = _serve_single_image(img_path)
                            img = ui.image(src).classes("w-full aspect-square object-cover cursor-zoom-in")
                            img.on("click", lambda _, s=src: show_lightbox(s))
                        else:
                            ui.label("文件不存在").classes("text-xs text-destructive-fg p-4")
                        with ui.column().classes("px-2 py-1.5 gap-0"):
                            ui.label(result.label).classes("text-xs font-semibold")
                            ui.label(f"相似度: {result.similarity:.4f}").classes("text-xs text-muted")
                            ui.label(img_path.as_posix()).classes(
                                "text-xs text-muted leading-snug whitespace-normal break-all"
                            )

        async def do_search() -> None:
            repo = state.repo_name
            query = state.query_path
            if not repo:
                ui.notify("请选择仓库", type="negative")
                return
            if not query or not Path(query).exists():
                ui.notify("请输入有效的图片路径", type="negative")
                return

            state.loading = True
            state.error = ""
            render_results.refresh()

            result = await ctx.task_manager.run_result(
                f"相似搜索: {repo}",
                search_similar,
                repo,
                Path(query),
                int(state.top_k or 10),
                skip_update=bool(state.skip_update),
            )

            state.loading = False
            if not result.ok or result.data is None:
                ctx.search_results = []
                state.error = result.message
                ui.notify(result.message, type="negative")
                render_results.refresh()
                return

            state.error = ""
            ctx.search_results = [
                SearchResultEntry(label=item.label, path=item.path, similarity=item.similarity) for item in result.data
            ]
            render_results.refresh()

        ui.button("搜索", icon="search", on_click=do_search)
        with ui.column().classes("w-full"):
            render_results()


_served_dirs: dict[str, str] = {}


def _serve_single_image(img_path: Path) -> str:
    parent = img_path.parent
    key = str(parent)
    if key not in _served_dirs:
        url_path = f"/search-images/{len(_served_dirs)}"
        app.add_media_files(url_path, parent)
        _served_dirs[key] = url_path
    return f"{_served_dirs[key]}/{quote(img_path.name, safe='')}"
