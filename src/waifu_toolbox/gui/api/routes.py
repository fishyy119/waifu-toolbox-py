import asyncio
import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated, cast

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from starlette.responses import FileResponse, StreamingResponse

from ...core import operations
from ...db.models import RepoInfo, RepoSummary
from ..services.library import build_directory_tree, directory_key, label_distribution
from ..services.task_manager import TaskManager
from ..utils.sorting import localized_sort_key
from .actions import submit_task
from .models import ErrorResponse, ImagePageResponse, LabelCount, RepoDetailResponse, TaskRequest, TaskResponse
from .presenters import present_task

router = APIRouter(
    prefix="/api",
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


def _tasks(request: Request) -> TaskManager:
    return cast("TaskManager", request.app.state.tasks)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/repos")
def repos() -> list[RepoInfo]:
    return operations.list_repo_infos()


@router.get("/repos/summary")
def repo_summaries() -> list[RepoSummary]:
    return operations.list_repos()


@router.get("/repos/{repo_name}")
def repo_detail(repo_name: str) -> RepoDetailResponse:
    info = operations.get_repo_info(repo_name)
    images = operations.get_repo_images(repo_name)
    if info is None or images is None:
        raise HTTPException(404, f"仓库 '{repo_name}' 不存在")
    return RepoDetailResponse(
        info=info,
        directories=build_directory_tree(images.images),
        labels=[LabelCount.model_validate(item) for item in label_distribution(images.images)],
    )


@router.get("/repos/{repo_name}/images")
def repo_images(
    repo_name: str,
    directory: str = "",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=10, le=500)] = 50,
) -> ImagePageResponse:
    result = operations.get_repo_images(repo_name)
    if result is None:
        raise HTTPException(404, f"仓库 '{repo_name}' 不存在")
    images = [image for image in result.images if directory_key(image.relative_path) == directory]
    page = min(page, max(1, (len(images) + page_size - 1) // page_size))
    start = (page - 1) * page_size
    return ImagePageResponse(items=images[start : start + page_size], total=len(images), page=page, page_size=page_size)


def _image_response(path: Path) -> FileResponse:
    if not path.is_file() or path.suffix.lower() not in _IMAGE_SUFFIXES:
        raise HTTPException(404, "图片文件不存在")
    return FileResponse(path)


@router.get("/repos/{repo_name}/image")
def repo_image(repo_name: str, relative_path: str) -> FileResponse:
    info = operations.get_repo_info(repo_name)
    if info is None:
        raise HTTPException(404, f"仓库 '{repo_name}' 不存在")
    root = Path(info.path).resolve()
    path = (root / relative_path.replace("\\", "/")).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(404, "图片文件不存在")
    return _image_response(path)


@router.get("/files/image")
def file_image(path: str) -> FileResponse:
    return _image_response(Path(path).expanduser().resolve())


@router.get("/files")
def browse_files(path: str = "", mode: str = "directory") -> dict[str, object]:
    root = Path(path).expanduser().resolve() if path else Path.home()
    if not root.is_dir():
        raise HTTPException(400, f"文件夹不存在: {root}")
    try:
        children = list(root.iterdir())
        children.sort(key=lambda item: (not item.is_dir(), localized_sort_key(item.name)))
        entries = [
            {"name": item.name, "path": str(item), "is_dir": item.is_dir()}
            for item in children
            if item.is_dir() or (mode == "file" and item.suffix.lower() in _IMAGE_SUFFIXES)
        ]
    except OSError as exc:
        raise HTTPException(403, f"无法读取目录: {root}") from exc
    roots = os.listdrives() if os.name == "nt" else ["/"]
    return {"path": str(root), "parent": str(root.parent), "roots": roots, "entries": entries}


@router.get("/tasks")
def tasks(request: Request) -> list[TaskResponse]:
    return [present_task(task) for task in _tasks(request).tasks]


@router.post("/tasks", status_code=202)
async def create_task(payload: TaskRequest, request: Request) -> TaskResponse:
    manager = _tasks(request)
    task_id = submit_task(manager, payload)
    task = manager.get(task_id)
    assert task is not None
    return present_task(task)


@router.delete("/tasks/completed")
async def clear_completed_tasks(request: Request) -> dict[str, int]:
    manager = _tasks(request)
    before = len(manager.tasks)
    manager.clear_completed()
    return {"removed": before - len(manager.tasks)}


@router.get("/tasks/events")
async def task_events(request: Request) -> StreamingResponse:
    manager = _tasks(request)

    async def stream() -> AsyncIterator[str]:
        # 每个客户端只保留最新快照，避免高频进度把慢客户端的队列撑大。
        queue: asyncio.Queue[None] = asyncio.Queue(maxsize=1)

        def changed() -> None:
            if queue.empty():
                queue.put_nowait(None)

        unsubscribe = manager.subscribe(changed)
        try:
            while not await request.is_disconnected():
                data = json.dumps(jsonable_encoder([present_task(task) for task in manager.tasks]), ensure_ascii=False)
                yield f"event: snapshot\ndata: {data}\n\n"
                try:
                    await asyncio.wait_for(queue.get(), timeout=15)
                    await asyncio.sleep(0.15)
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            unsubscribe()

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/tasks/{task_id}")
def task_detail(task_id: str, request: Request) -> TaskResponse:
    task = _tasks(request).get(task_id)
    if task is None:
        raise HTTPException(404, "任务不存在或已经清除")
    return present_task(task)
