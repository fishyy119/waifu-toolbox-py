from pathlib import Path

from nicegui import ui

from ...db.operations import create_repo, list_repo_infos
from ..components.badges import badge, feature_badge
from ..components.file_picker import folder_picker
from ..components.layout import page_layout
from ..services.task_manager import task_manager


def render() -> None:
    page_layout("/")

    with ui.column().classes("w-full p-6 gap-4 max-w-5xl"):

        @ui.refreshable
        def render_repos() -> None:
            infos = list_repo_infos()
            if not infos:
                ui.label("暂无仓库，请使用上方按钮或 CLI 创建仓库。").classes("text-sm text-muted")
                return

            for info in infos:
                with (
                    ui.card()
                    .classes("w-full cursor-pointer")
                    .on("click", lambda _, n=info.name: ui.navigate.to(f"/repo/{n}"))
                ):
                    with ui.row().classes("items-center w-full justify-between"):
                        with ui.column().classes("gap-0"):
                            ui.label(info.name).classes("text-sm font-semibold")
                            ui.label(info.path).classes("text-xs text-muted")
                        with ui.row().classes("gap-2"):
                            badge(f"{info.total_images} 张图片")
                            badge(f"{info.label_count} 标签")
                            feature_badge("CCIP", info.ccip_count, info.total_images)
                            feature_badge("DreamSim", info.dreamsim_count, info.total_images)

        with ui.row().classes("items-center justify-between w-full"):
            ui.label("仓库管理").classes("text-2xl font-semibold tracking-tight")
            ui.button("创建仓库", icon="add", on_click=lambda: create_dialog.open())

        with ui.column().classes("w-full gap-3"):
            render_repos()

    with ui.dialog() as create_dialog:
        with ui.card().classes("w-96"):
            ui.label("创建仓库").classes("text-lg font-semibold")
            ui.label("从已分类的图片文件夹创建仓库索引").classes("text-sm text-muted")

            name_input = ui.input(label="仓库名称", placeholder="输入仓库名称").classes("w-full")
            path_input = folder_picker(label="图片文件夹路径")
            ccip_check = ui.checkbox("提取 CCIP 特征")
            dreamsim_check = ui.checkbox("提取 DreamSim 特征")

            with ui.row().classes("justify-end gap-2 mt-2"):
                ui.button("取消", on_click=create_dialog.close).props("flat")

                async def do_create():
                    name = name_input.value
                    path = path_input.value
                    if not name:
                        ui.notify("请输入仓库名称", type="negative")
                        return
                    if not path or not Path(path).exists():
                        ui.notify("请输入有效的文件夹路径", type="negative")
                        return

                    result = await task_manager.run_result(
                        f"创建仓库: {name}",
                        create_repo,
                        name,
                        Path(path),
                        extract_ccip=bool(ccip_check.value),
                        extract_dreamsim=bool(dreamsim_check.value),
                    )
                    if result.ok:
                        ui.notify(result.message, type="positive")
                        create_dialog.close()
                        render_repos.refresh()
                    else:
                        ui.notify(result.message, type="negative")

                ui.button("创建", on_click=do_create)
