from collections import Counter
from pathlib import Path
from typing import TypedDict

from nicegui import ui

from ...db.operations import (
    change_repo_path,
    deduplicate_repo,
    flatten_repo,
    get_repo_images,
    get_repo_info,
    purge_repo,
    rename_repo,
    update_repo,
)
from ..components.badges import badge, feature_badge
from ..components.file_picker import folder_picker
from ..components.image_viewer import ImageItem, image_viewer, serve_repo_images
from ..components.layout import THEME, page_layout
from ..services.task_manager import task_manager


def render(repo_name: str):
    page_layout(f"/repo/{repo_name}")

    with ui.column().classes("w-full p-6 gap-4 max-w-5xl"):
        info = get_repo_info(repo_name)
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
                _update_section(repo_name)
                _purge_button(repo_name)
                _deduplicate_button(repo_name)
                _flatten_button(repo_name)

            ui.separator().classes("my-2")

            with ui.row().classes("gap-2"):
                _rename_button(repo_name)
                _change_path_button(repo_name)

        result = get_repo_images(repo_name)
        if result is None:
            return
        url_prefix = serve_repo_images(repo_name, result.repo_path)
        images = result.images

        all_images: list[ImageItem] = [{"relative_path": img.relative_path, "label": img.label} for img in images]
        labels = sorted(set(img.label for img in images))

        label_counts = Counter(img.label for img in images)
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

        class _ViewState(TypedDict):
            label: str

        view_state: _ViewState = {"label": ""}

        with ui.row().classes("items-center gap-4 flex-wrap"):
            ui.select(
                label="标签筛选",
                options=["(全部)"] + labels,
                value="(全部)",
                on_change=lambda e: _set_label(e.value),
            ).classes("min-w-[160px]")
            columns_input = (
                ui.number(
                    label="列数",
                    value=0,
                    min=0,
                    max=20,
                    step=1,
                    on_change=lambda _: render_grid(),
                )
                .classes("w-24")
                .tooltip("0 = 自动")
            )
            page_size_input = ui.number(
                label="每页数量",
                value=50,
                min=10,
                max=500,
                step=10,
                on_change=lambda _: render_grid(),
            ).classes("w-24")
            view_mode_toggle = ui.toggle(
                {"grid": "网格", "masonry": "瀑布流"},
                value="grid",
                on_change=lambda _: render_grid(),
            ).props("")

        grid_container = ui.column().classes("w-full")

        def _set_label(label: str) -> None:
            view_state["label"] = "" if label == "(全部)" else label
            render_grid()

        def render_grid() -> None:
            grid_container.clear()
            filtered = all_images
            lbl = view_state["label"]
            if lbl:
                filtered = [img for img in all_images if img["label"] == lbl]
            with grid_container:
                if not filtered:
                    ui.label("无匹配图片").classes("text-sm text-muted")
                else:
                    image_viewer(
                        filtered,
                        url_prefix,
                        page_size=int(page_size_input.value or 50),
                        columns=int(columns_input.value or 0),
                        mode="grid" if view_mode_toggle.value == "grid" else "masonry",
                    )

        render_grid()


def _update_section(repo_name: str):
    def do_update(ccip: bool, dreamsim: bool):
        task_manager.submit(
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


def _purge_button(repo_name: str):
    async def do_purge():
        result = await task_manager.run_result(f"清理失效: {repo_name}", purge_repo, repo_name)
        ui.notify(result.message, type="positive" if result.ok else "negative")

    ui.button("清理失效", icon="cleaning_services", on_click=do_purge).props("outline").tooltip(
        "移除磁盘上已不存在的图片索引"
    )


def _deduplicate_button(repo_name: str):
    async def do_dedup():
        result = await task_manager.run_result(f"去重: {repo_name}", deduplicate_repo, repo_name)
        ui.notify(result.message, type="positive" if result.ok else "negative")

    ui.button("去重", icon="filter_alt", on_click=do_dedup).props("outline").tooltip("基于文件哈希删除重复图片")


def _flatten_button(repo_name: str):
    def do_flatten():
        task_manager.submit(
            f"扁平化: {repo_name}",
            flatten_repo,
            repo_name,
        )
        ui.notify("扁平化任务已提交")

    ui.button("扁平化", icon="folder_copy", on_click=do_flatten).props("outline").tooltip("将子目录结构展平为单层")


def _rename_button(repo_name: str):
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
                    result = await task_manager.run_result(
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


def _change_path_button(repo_name: str):
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
                    result = await task_manager.run_result(
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
