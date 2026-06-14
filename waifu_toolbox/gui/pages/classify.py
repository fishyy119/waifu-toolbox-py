from pathlib import Path

from nicegui import ui

from ...db.operations import list_repos
from ..components.file_picker import folder_picker
from ..components.layout import page_layout
from ..services.task_manager import task_manager


def render():
    page_layout("/classify")

    with ui.column().classes("w-full p-6 gap-4 max-w-3xl"):
        ui.label("图片分类").classes("text-2xl font-semibold tracking-tight")
        ui.label("基于 CCIP 特征聚类，将未标注图片按角色分类").classes("text-sm text-muted")

        repos = list_repos()
        repo_names = [r.name for r in repos]

        with ui.card().classes("w-full"):
            mode = ui.toggle(
                {"ref": "参考仓库分类", "cluster": "独立聚类"},
                value="ref",
            )

            repo_select = (
                ui.select(
                    label="参考仓库",
                    options=repo_names,
                    value=repo_names[0] if repo_names else None,
                )
                .classes("w-64")
                .bind_visibility_from(mode, "value", lambda v: v == "ref")
            )

            folder_input = folder_picker(label="待分类图片文件夹")

            num_ref = (
                ui.number(
                    label="每类参考数量",
                    value=20,
                    min=5,
                    max=100,
                    step=5,
                )
                .classes("w-32")
                .bind_visibility_from(mode, "value", lambda v: v == "ref")
            )

            inplace_check = ui.checkbox("原地分类（移动文件而非复制）").bind_visibility_from(
                mode, "value", lambda v: v == "cluster"
            )

        def start_classify():
            folder = folder_input.value
            if not folder or not Path(folder).exists():
                ui.notify("请输入有效的文件夹路径", type="negative")
                return

            if mode.value == "ref":
                if not repo_select.value:
                    ui.notify("请选择参考仓库", type="negative")
                    return
                from ...core.classification import classify_by_ccip

                task_manager.submit(
                    f"分类: {Path(folder).name}",
                    classify_by_ccip,
                    repo_select.value,
                    Path(folder),
                    int(num_ref.value or 20),
                )
            else:
                from ...core.classification import just_cluster_by_ccip

                task_manager.submit(
                    f"聚类: {Path(folder).name}",
                    just_cluster_by_ccip,
                    Path(folder),
                    bool(inplace_check.value),
                )
            ui.notify("任务已提交")

        ui.button("开始分类", icon="play_arrow", on_click=start_classify)
