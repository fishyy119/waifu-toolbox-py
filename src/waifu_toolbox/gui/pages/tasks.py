from nicegui import ui

from ..components.badges import status_badge
from ..components.layout import page_layout
from ..services.task_manager import task_manager


def render() -> None:
    page_layout("/tasks")

    with ui.column().classes("w-full p-6 gap-4 max-w-3xl"):

        @ui.refreshable
        def render_tasks() -> None:
            tasks = task_manager.tasks
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
            task_manager.clear_completed()
            render_tasks.refresh()

        with ui.row().classes("items-center justify-between w-full"):
            ui.label("任务队列").classes("text-2xl font-semibold tracking-tight")
            ui.button("清除已完成", icon="delete_sweep", on_click=clear_completed_tasks).props("flat")

        with ui.column().classes("w-full gap-2"):
            render_tasks()

        ui.timer(0.5, render_tasks.refresh)
