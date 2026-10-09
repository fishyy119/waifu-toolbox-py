from pathlib import Path
from typing import cast

from ...core.convert import ConvertResult
from ...core.repository import ImageRepo
from ...db.models import CacheClearResult
from ..services.task_manager import TaskInfo
from .models import SearchMatch, TaskKind, TaskResponse, TaskResultResponse


def present_task(task: TaskInfo) -> TaskResponse:
    """隔离业务结果类型，HTTP 响应和 SSE 快照使用同一输出契约。"""
    result = None
    message = ""
    if task.status == "completed":
        result = TaskResultResponse()
        message = {
            "repo.create": "仓库创建成功",
            "repo.rename": "仓库已重命名",
            "repo.path": "路径已更新",
            "repo.delete": "仓库索引已删除（未删除磁盘文件）",
            "sort": "排序完成",
        }.get(task.kind, "任务已完成")
        data = task.result_data
        if isinstance(data, Path):
            result.output_path = str(data)
            prefix = {"classify.reference": "报告已生成", "classify.cluster": "聚类完成"}.get(task.kind, "输出文件夹")
            message = f"{prefix}: {data}"
        elif isinstance(data, ImageRepo.ScanInitResult):
            result.details = data.label_mismatches
            if data.label_mismatches:
                message += f"，{len(data.label_mismatches)} 条标签冲突（同 hash 不同标签，仅保留首次出现）"
        elif isinstance(data, ConvertResult):
            result.details = data.errors
            result.counts = {"converted": data.converted, "failed": data.failed}
            message = f"转换 {data.converted} 张"
            if data.failed:
                message += f"，失败 {data.failed} 张"
        elif isinstance(data, ImageRepo.DeduplicateResult):
            result.details = data.label_mismatches
            result.counts = {"deleted": data.deleted}
            parts: list[str] = []
            if data.deleted > 0:
                parts.append(f"删除了 {data.deleted} 张重复图片")
            if data.label_mismatches:
                parts.append(f"{len(data.label_mismatches)} 条标签不一致")
            message = "、".join(parts) if parts else "未发现重复"
        elif isinstance(data, ImageRepo.UpdateResult):
            result.counts = {"new_images": data.new_images, "updated_labels": data.updated_labels}
            message = (
                f"新增 {data.new_images} 张图片，更新 {data.updated_labels} 个标签"
                if data.new_images or data.updated_labels
                else "仓库已是最新"
            )
        elif isinstance(data, CacheClearResult):
            result.counts = {"ccip_deleted": data.ccip_deleted, "dreamsim_deleted": data.dreamsim_deleted}
            message = (
                f"已清空缓存（CCIP {data.ccip_deleted} 条、DreamSim {data.dreamsim_deleted} 条），"
                f"共 {data.ccip_deleted + data.dreamsim_deleted} 条"
            )
        elif isinstance(data, int):
            result.counts = {"removed": data}
            message = f"清除了 {data} 条失效记录" if data > 0 else "没有需要清除的记录"
        elif task.kind == "search" and isinstance(data, list):
            result.search_results = [SearchMatch.model_validate(item) for item in cast("list[object]", data)]
            message = f"找到 {len(result.search_results)} 条结果"
    return TaskResponse(
        id=task.id,
        name=task.name,
        kind=cast("TaskKind", task.kind),
        status=task.status,
        progress=task.progress,
        progress_desc=task.progress_desc,
        progress_text=task.progress_text,
        result_text=message,
        error=task.error,
        created_at=task.created_at,
        result=result,
    )
