from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from nicegui import PageArguments, ui

from ...db.operations import (
    change_repo_path,
    deduplicate_repo,
    delete_repo,
    flatten_repo,
    get_repo_images,
    get_repo_info,
    purge_repo,
    rename_repo,
    update_repo,
)
from ..components.badges import badge, feature_badge
from ..components.directory_tree import (
    DirectoryTreeNode,
    DirectoryTreeState,
    directory_tree,
)
from ..components.file_picker import folder_picker
from ..components.image_viewer import ImageItem, image_viewer, serve_repo_images
from ..components.layout import THEME
from ..context import DrawerPanel, GuiContext
from ..utils.sorting import localized_sort_key
from ..utils.storage import prefs


@dataclass
class _DirectoryBranch:
    key: str
    label: str
    children: dict[str, "_DirectoryBranch"] = field(default_factory=lambda: _new_branch_children())


@dataclass(frozen=True)
class _DirectoryBrowser:
    tree_nodes: list[DirectoryTreeNode]
    direct_images_by_dir: dict[str, list[ImageItem]]
    preorder_keys: tuple[str, ...]


def _new_branch_children() -> dict[str, _DirectoryBranch]:
    return {}


def _split_relative_path(relative_path: str) -> tuple[str, ...]:
    normalized = relative_path.replace("\\", "/").strip("/")
    if not normalized:
        return ()
    return tuple(part for part in normalized.split("/") if part)


def _build_tree_nodes(
    branches: dict[str, _DirectoryBranch],
    direct_images_by_dir: dict[str, list[ImageItem]],
    preorder_keys: list[str],
) -> list[DirectoryTreeNode]:
    tree_nodes: list[DirectoryTreeNode] = []
    for branch_name in sorted(branches, key=localized_sort_key):
        branch = branches[branch_name]
        preorder_keys.append(branch.key)
        direct_images_by_dir.setdefault(branch.key, [])
        children = _build_tree_nodes(branch.children, direct_images_by_dir, preorder_keys)
        tree_nodes.append({"id": branch.key, "label": branch.label, "children": children})
    return tree_nodes


def _build_directory_browser(images: list[ImageItem]) -> _DirectoryBrowser:
    roots: dict[str, _DirectoryBranch] = {}
    direct_images_by_dir: dict[str, list[ImageItem]] = {}

    for image in images:
        parts = _split_relative_path(image["relative_path"])
        if len(parts) < 2:
            continue

        cursor = roots
        branch: _DirectoryBranch | None = None
        key_parts: list[str] = []
        for part in parts[:-1]:
            key_parts.append(part)
            current_key = "/".join(key_parts)
            next_branch = cursor.get(part)
            if next_branch is None:
                next_branch = _DirectoryBranch(key=current_key, label=part)
                cursor[part] = next_branch
            branch = next_branch
            cursor = next_branch.children

        if branch is None:
            continue

        direct_images_by_dir.setdefault(branch.key, []).append(image)

    preorder_keys: list[str] = []
    tree_nodes = _build_tree_nodes(roots, direct_images_by_dir, preorder_keys)
    return _DirectoryBrowser(
        tree_nodes=tree_nodes,
        direct_images_by_dir=direct_images_by_dir,
        preorder_keys=tuple(preorder_keys),
    )


def _default_directory_key(browser: _DirectoryBrowser) -> str:
    for key in browser.preorder_keys:
        if browser.direct_images_by_dir.get(key):
            return key
    return browser.preorder_keys[0] if browser.preorder_keys else ""


def render(ctx: GuiContext, repo_name: str, page_args: PageArguments) -> None:

    info = get_repo_info(repo_name)
    result = get_repo_images(repo_name) if info is not None else None
    all_images: list[ImageItem] = []
    if result is not None:
        all_images = [{"relative_path": img.relative_path, "label": img.label} for img in result.images]

    directory_browser = _build_directory_browser(all_images)
    default_key = _default_directory_key(directory_browser)
    saved_selected_dir = prefs.selected_dirs.get(repo_name, "") or default_key
    if saved_selected_dir not in directory_browser.direct_images_by_dir:
        saved_selected_dir = default_key
    tree_state = DirectoryTreeState(selected_key=saved_selected_dir)

    @ui.refreshable
    def render_grid() -> None:
        selected_key = tree_state.selected_key
        filtered = directory_browser.direct_images_by_dir.get(selected_key, [])

        if not selected_key:
            ui.label("当前索引中暂无可浏览目录").classes("text-sm text-muted")
        elif not filtered:
            ui.label("当前目录无直属图片，请继续选择子目录").classes("text-sm text-muted")
        else:
            image_viewer(
                filtered,
                url_prefix,
                page_size=int(page_size_input.value or 50),
                columns=int(columns_input.value or 5),
                mode="grid" if view_mode_toggle.value == "grid" else "masonry",
            )

    def render_directory_panel() -> None:
        if not directory_browser.tree_nodes:
            ui.label("当前索引中暂无可浏览目录").classes("text-sm text-muted px-2")
            return

        def _on_dir_selected(key: str) -> None:
            if key:
                prefs.selected_dirs[repo_name] = key
            render_grid.refresh()

        directory_tree(
            nodes=directory_browser.tree_nodes,
            state=tree_state,
            on_selection_change=_on_dir_selected,
        )

    ctx.activate_route(
        page_args.path,
        drawer_panels=[
            DrawerPanel(
                key="tree",
                label="目录树",
                render=render_directory_panel,
                icon="account_tree",
            )
        ],
        default_panel="tree",
    )

    with ui.column().classes("w-full p-6 gap-4 max-w-5xl"):
        if info is None:
            ui.label(f"仓库 '{repo_name}' 不存在").classes("text-sm text-destructive-fg")
            return

        with ui.card().classes("w-full"):
            with ui.row().classes("items-center gap-4"):
                ui.label(info.name).classes("text-lg font-semibold tracking-tight")
                ui.label(info.path).classes("text-xs text-muted font-mono")
            with ui.row().classes("gap-2 mt-2"):
                badge(f"{info.total_images} 张图片")
                badge(f"{info.label_count} 标签")
                feature_badge("CCIP", info.ccip_count, info.total_images)
                feature_badge("DreamSim", info.dreamsim_count, info.total_images)

        with ui.card().classes("w-full"):
            ui.label("仓库管理").classes("text-sm font-semibold")

            with ui.row().classes("gap-2 mt-2 flex-wrap"):
                _update_section(ctx, repo_name)
                _purge_button(ctx, repo_name)
                _deduplicate_button(ctx, repo_name)
                _flatten_button(ctx, repo_name)

            ui.separator().classes("my-2")

            with ui.row().classes("gap-2"):
                _rename_button(ctx, repo_name)
                _change_path_button(ctx, repo_name)
                _delete_button(ctx, repo_name)

        if result is None:
            return
        url_prefix = serve_repo_images(repo_name, result.repo_path)
        label_counts = Counter(img["label"] for img in all_images)
        sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)
        if sorted_labels:
            with ui.card().classes("w-full"):
                ui.label("标签分布").classes("text-sm font-semibold")
                chart_labels = [lb for lb, _ in sorted_labels[:30]]
                chart_values = [cnt for _, cnt in sorted_labels[:30]]
                ui.echart(
                    {
                        "tooltip": {"trigger": "axis"},
                        "xAxis": {
                            "type": "category",
                            "data": chart_labels,
                            "axisLabel": {"rotate": 45, "fontSize": 10},
                        },
                        "yAxis": {"type": "value"},
                        "series": [{"type": "bar", "data": chart_values, "color": THEME["primary"]}],
                    }
                ).classes("w-full h-64")
                if len(sorted_labels) > 30:
                    ui.label(f"（仅显示前 30 个标签，共 {len(sorted_labels)} 个）").classes("text-xs text-muted")

        with ui.row().classes("items-center gap-4 flex-wrap"):
            columns_input = (
                ui.number(
                    label="列数",
                    min=1,
                    max=20,
                    step=1,
                    on_change=lambda _: render_grid.refresh(),
                )
                .classes("w-24")
                .bind_value(prefs, "viewer_columns")
            )

            page_size_input = (
                ui.number(
                    label="每页数量",
                    min=10,
                    max=500,
                    step=10,
                    on_change=lambda _: render_grid.refresh(),
                )
                .classes("w-24")
                .bind_value(prefs, "viewer_page_size")
            )

            view_mode_toggle = (
                ui.toggle(
                    {"grid": "网格", "masonry": "瀑布流"},
                    on_change=lambda _: render_grid.refresh(),
                )
                .props("")
                .bind_value(prefs, "viewer_view_mode")
            )

        render_grid()


def _update_section(ctx: GuiContext, repo_name: str) -> None:
    def do_update(ccip: bool, dreamsim: bool):
        ctx.task_manager.submit(
            f"更新仓库: {repo_name}",
            update_repo,
            repo_name,
            extract_ccip=ccip,
            extract_dreamsim=dreamsim,
        )
        ui.notify("更新任务已提交")

    with ui.dropdown_button("更新仓库", icon="refresh").props("outline"):
        ui.item("仅同步索引", on_click=lambda: do_update(False, False))
        ui.item("同步 + 提取 CCIP", on_click=lambda: do_update(True, False))
        ui.item("同步 + 提取 DreamSim", on_click=lambda: do_update(False, True))
        ui.item("同步 + 提取全部特征", on_click=lambda: do_update(True, True))


def _purge_button(ctx: GuiContext, repo_name: str) -> None:
    async def do_purge():
        result = await ctx.task_manager.run_result(f"清理失效: {repo_name}", purge_repo, repo_name)
        ui.notify(result.message, type="positive" if result.ok else "negative")

    ui.button("清理失效", icon="cleaning_services", on_click=do_purge).props("outline").tooltip(
        "移除磁盘上已不存在的图片索引"
    )


def _deduplicate_button(ctx: GuiContext, repo_name: str) -> None:
    async def do_dedup():
        result = await ctx.task_manager.run_result(f"去重: {repo_name}", deduplicate_repo, repo_name)
        ui.notify(result.message, type="positive" if result.ok else "negative")

    ui.button("去重", icon="filter_alt", on_click=do_dedup).props("outline").tooltip("基于文件哈希删除重复图片")


def _flatten_button(ctx: GuiContext, repo_name: str) -> None:
    def do_flatten():
        ctx.task_manager.submit(
            f"扁平化: {repo_name}",
            flatten_repo,
            repo_name,
        )
        ui.notify("扁平化任务已提交")

    ui.button("扁平化", icon="folder_copy", on_click=do_flatten).props("outline").tooltip("将子目录结构展平为单层")


def _rename_button(ctx: GuiContext, repo_name: str) -> None:
    with ui.dialog() as dialog:
        with ui.card().classes("w-80"):
            ui.label("重命名仓库").classes("text-sm font-semibold")
            new_name_input = ui.input(label="新名称", value=repo_name).classes("w-full")
            with ui.row().classes("justify-end gap-2 mt-2"):
                ui.button("取消", on_click=dialog.close).props("flat")

                async def do_rename():
                    new_name = new_name_input.value
                    if not new_name or new_name == repo_name:
                        return
                    result = await ctx.task_manager.run_result(
                        f"重命名仓库: {repo_name}",
                        rename_repo,
                        repo_name,
                        new_name,
                    )
                    if result.ok:
                        ui.notify(result.message, type="positive")
                        dialog.close()
                        ui.navigate.to(f"/repo/{new_name}")
                    else:
                        ui.notify(result.message, type="negative")

                ui.button("确认", on_click=do_rename)

    ui.button("重命名", icon="edit", on_click=dialog.open).props("flat")


def _change_path_button(ctx: GuiContext, repo_name: str) -> None:
    with ui.dialog() as dialog:
        with ui.card().classes("w-96"):
            ui.label("修改仓库路径").classes("text-sm font-semibold")
            path_input = folder_picker(label="新路径")
            with ui.row().classes("justify-end gap-2 mt-2"):
                ui.button("取消", on_click=dialog.close).props("flat")

                async def do_change():
                    new_path = path_input.value
                    if not new_path:
                        return
                    result = await ctx.task_manager.run_result(
                        f"修改路径: {repo_name}",
                        change_repo_path,
                        repo_name,
                        Path(new_path),
                    )
                    if result.ok:
                        ui.notify(result.message, type="positive")
                        dialog.close()
                        ui.navigate.to(f"/repo/{repo_name}")
                    else:
                        ui.notify(result.message, type="negative")

                ui.button("确认", on_click=do_change)

    ui.button("修改路径", icon="folder_open", on_click=dialog.open).props("flat")


def _delete_button(ctx: GuiContext, repo_name: str) -> None:
    with ui.dialog() as dialog:
        with ui.card().classes("w-96"):
            ui.label("删除仓库").classes("text-sm font-semibold text-destructive-fg")
            ui.label("仅删除数据库中的仓库索引和关联图片记录，不会删除磁盘上的原始文件。").classes("text-sm text-muted")
            confirm_input = ui.input(label=f"输入仓库名称以确认：{repo_name}").classes("w-full")

            with ui.row().classes("justify-end gap-2 mt-2"):
                ui.button("取消", on_click=dialog.close).props("flat")

                async def do_delete():
                    if confirm_input.value != repo_name:
                        ui.notify("请输入完整仓库名称以确认删除", type="negative")
                        return
                    result = await ctx.task_manager.run_result(
                        f"删除仓库: {repo_name}",
                        delete_repo,
                        repo_name,
                    )
                    if result.ok:
                        ui.notify(result.message, type="positive")
                        dialog.close()
                        ui.navigate.to("/")
                    else:
                        ui.notify(result.message, type="negative")

                ui.button("删除仓库", icon="delete", on_click=do_delete).props("color=negative")

    def open_dialog() -> None:
        confirm_input.value = ""
        dialog.open()

    ui.button("删除仓库", icon="delete", on_click=open_dialog).props("flat color=negative")
