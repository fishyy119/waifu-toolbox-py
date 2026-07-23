from typing import Any

from nicegui import PageArguments, ui

from ..components.badges import status_badge
from ..context import GuiContext


def render(ctx: GuiContext, page_args: PageArguments) -> None:
    ctx.activate_route(page_args.path)

    with ui.column().classes("w-full p-6 gap-4 max-w-3xl"):

        @ui.refreshable
        def render_tasks() -> None:
            tasks = ctx.task_manager.tasks
            if not tasks:
                ui.label("暂无任务").classes("text-sm text-muted")
                return

            for t in tasks:
                with ui.card().classes("w-full"):
                    with ui.row().classes("items-center justify-between w-full"):
                        with ui.row().classes("items-center gap-2"):
                            ui.label(t.name).classes("text-sm font-semibold")
                            ui.label(t.created_at.strftime("%H:%M:%S")).classes("text-xs text-muted")
                        status_badge(t.status)

                    if t.status == "running":
                        if t.progress_desc:
                            ui.label(t.progress_desc).classes("text-xs text-muted mt-1")
                        ui.linear_progress(value=t.progress, show_value=False).classes("w-full")
                        if t.progress_text:
                            ui.label(t.progress_text).classes("text-xs text-muted")

                    if t.status == "completed" and t.result_text:
                        ui.label(t.result_text).classes("text-xs text-success mt-1")

                    if t.status == "failed":
                        ui.label(t.error).classes("text-xs text-destructive-fg mt-1")

        def clear_completed_tasks() -> None:
            ctx.task_manager.clear_completed()
            render_tasks.refresh()

        with ui.row().classes("items-center justify-between w-full"):
            ui.label("任务队列").classes("text-2xl font-semibold tracking-tight")
            ui.button("清除已完成", icon="delete_sweep", on_click=clear_completed_tasks).props("flat")

        with ui.column().classes("w-full gap-2"):
            render_tasks()

        def refresh_tasks(_: Any) -> None:
            render_tasks.refresh()

        unsubscribe = ctx.task_manager.subscribe(refresh_tasks)
        ctx.register_route_disposer(unsubscribe)
