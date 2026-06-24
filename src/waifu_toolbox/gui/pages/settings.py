from nicegui import ui

from ...db.operations import clear_cache
from ..components.layout import page_layout
from ..services.task_manager import task_manager


def render():
    page_layout("/settings")

    with ui.column().classes("w-full p-6 gap-4 max-w-3xl"):
        ui.label("设置").classes("text-2xl font-semibold tracking-tight")

        with ui.card().classes("w-full"):
            ui.label("缓存管理").classes("text-sm font-semibold")
            ui.label("清空已缓存的图片特征向量。清空后下次提取特征时需重新计算。").classes("text-sm text-muted")

            with ui.row().classes("gap-2 mt-3"):

                async def do_clear(ccip: bool = False, dreamsim: bool = False):
                    result = await task_manager.run_result(
                        "清理特征缓存",
                        clear_cache,
                        ccip=ccip,
                        dreamsim=dreamsim,
                    )
                    ui.notify(result.message, type="positive" if result.ok else "negative")

                async def clear_ccip():
                    await do_clear(ccip=True)

                async def clear_dreamsim():
                    await do_clear(dreamsim=True)

                async def clear_all():
                    await do_clear()

                ui.button("清空 CCIP 缓存", on_click=clear_ccip).props("outline")
                ui.button("清空 DreamSim 缓存", on_click=clear_dreamsim).props("outline")
                ui.button("清空全部缓存", on_click=clear_all).props("outline color=negative")
