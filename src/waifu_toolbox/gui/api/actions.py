from functools import partial
from pathlib import Path

from fastapi import HTTPException

from ...core import operations
from ..services.task_manager import TaskManager
from .models import (
    ClassifyCluster,
    ClassifyReference,
    ConvertImages,
    RepoAction,
    RepoCreate,
    RepoDelete,
    RepoPath,
    RepoRename,
    SearchImages,
    SortImages,
    TaskRequest,
)


def _directory(path: Path) -> Path:
    path = path.expanduser().resolve()
    if not path.is_dir():
        raise HTTPException(400, f"请输入有效的文件夹路径: {path}")
    return path


def submit_task(tasks: TaskManager, payload: TaskRequest) -> str:
    """验证业务参数，将各类操作提交到同一串行队列。"""
    submit = partial(tasks.submit, kind=payload.kind)
    if isinstance(payload, RepoCreate):
        return submit(
            f"创建仓库: {payload.repo_name}",
            operations.create_repo,
            payload.repo_name,
            _directory(payload.path),
            extract_ccip=payload.ccip,
            extract_dreamsim=payload.dreamsim,
        )
    if isinstance(payload, RepoAction):
        if payload.kind == "repo.update":
            return submit(
                f"更新仓库: {payload.repo_name}",
                operations.update_repo,
                payload.repo_name,
                extract_ccip=payload.ccip,
                extract_dreamsim=payload.dreamsim,
            )
        actions = {
            "repo.purge": ("清理失效", operations.purge_repo),
            "repo.deduplicate": ("去重", operations.deduplicate_repo),
            "repo.flatten": ("扁平化", operations.flatten_repo),
        }
        label, action = actions[payload.kind]
        return submit(f"{label}: {payload.repo_name}", action, payload.repo_name)
    if isinstance(payload, RepoRename):
        return submit(f"重命名仓库: {payload.repo_name}", operations.rename_repo, payload.repo_name, payload.new_name)
    if isinstance(payload, RepoPath):
        return submit(
            f"修改路径: {payload.repo_name}", operations.change_repo_path, payload.repo_name, _directory(payload.path)
        )
    if isinstance(payload, RepoDelete):
        if payload.confirmation != payload.repo_name:
            raise HTTPException(400, "请输入完整仓库名称以确认删除")
        return submit(f"删除仓库: {payload.repo_name}", operations.delete_repo, payload.repo_name)
    if isinstance(payload, ClassifyReference):
        from ...core.classification import classify_by_ccip

        path = _directory(payload.path)
        return submit(f"分类: {path.name}", classify_by_ccip, payload.repo_name, path, payload.num_references)
    if isinstance(payload, ClassifyCluster):
        from ...core.classification import just_cluster_by_ccip

        path = _directory(payload.path)
        return submit(f"聚类: {path.name}", just_cluster_by_ccip, path, payload.inplace)
    if isinstance(payload, SortImages):
        from ...core.sort import sort_images_by_perceptual_similarity

        path = _directory(payload.path)
        return submit(f"排序: {path.name}", sort_images_by_perceptual_similarity, path, payload.avoid_sorted)
    if isinstance(payload, ConvertImages):
        from ...core.convert import convert_images

        path = _directory(payload.path)
        return tasks.submit(
            f"转换: {path.name}", convert_images, path, payload.replace, payload.source_format, kind=payload.kind
        )
    if isinstance(payload, SearchImages):
        path = payload.path.expanduser().resolve()
        if not path.is_file():
            raise HTTPException(400, "请输入有效的图片路径")
        return submit(
            f"相似搜索: {payload.repo_name}",
            operations.search_similar,
            payload.repo_name,
            path,
            payload.top_k,
            skip_update=payload.skip_update,
        )
    return submit("清理特征缓存", operations.clear_cache, ccip=payload.ccip, dreamsim=payload.dreamsim)
