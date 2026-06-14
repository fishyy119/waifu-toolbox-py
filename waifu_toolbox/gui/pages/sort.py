from pathlib import Path

from nicegui import ui

from ..components.file_picker import folder_picker
from ..components.layout import page_layout
from ..services.task_manager import task_manager


def render():
    page_layout("/sort")

    with ui.column().classes("w-full p-6 gap-4 max-w-3xl"):
        ui.label("图片排序").classes("text-2xl font-semibold tracking-tight")
        ui.label("基于 DreamSim 感知相似度排序，使相似图片相邻").classes("text-sm text-muted")

        with ui.card().classes("w-full"):
            folder_input = folder_picker(label="图片文件夹")

            avoid_sorted = ui.checkbox("跳过已排序目录", value=True)

        def start_sort():
            folder = folder_input.value
            if not folder or not Path(folder).exists():
                ui.notify("请输入有效的文件夹路径", type="negative")
                return

            from ...core.sort import sort_images_by_perceptual_similarity

            task_manager.submit(
                f"排序: {Path(folder).name}",
                sort_images_by_perceptual_similarity,
                Path(folder),
                bool(avoid_sorted.value),
            )
            ui.notify("任务已提交")

        ui.button("开始排序", icon="play_arrow", on_click=start_sort)
