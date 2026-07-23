from pathlib import Path

from nicegui import PageArguments, ui

from ..components.file_picker import folder_picker
from ..context import GuiContext


def render(ctx: GuiContext, page_args: PageArguments) -> None:
    ctx.activate_route(page_args.path)

    with ui.column().classes("w-full p-6 gap-4 max-w-3xl"):
        ui.label("格式转换").classes("text-2xl font-semibold tracking-tight")
        ui.label("将图片批量转换为 WebP 格式").classes("text-sm text-muted")

        with ui.card().classes("w-full"):
            folder_input = folder_picker(label="图片文件夹")

            source_format = ui.select(
                label="源格式",
                options=["bmp", "jpg", "jpeg", "png"],
                value="bmp",
            ).classes("w-48")

            replace_check = ui.checkbox("转换后删除原文件")

        def start_convert():
            folder = folder_input.value
            if not folder or not Path(folder).exists():
                ui.notify("请输入有效的文件夹路径", type="negative")
                return

            from ...core.convert import convert_images

            ctx.task_manager.submit(
                f"转换: {Path(folder).name}",
                convert_images,
                Path(folder),
                bool(replace_check.value),
                source_format.value,
            )
            ui.notify("任务已提交")

        ui.button("开始转换", icon="play_arrow", on_click=start_convert)
