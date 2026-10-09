import asyncio
import inspect
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from typing import Any, Literal
from uuid import uuid4

from ...utils.progress import ProgressReporter

TaskSubscriber = Callable[[], None]


@dataclass
class TaskInfo:
    id: str
    name: str
    kind: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    progress: float = 0.0
    progress_desc: str = ""
    progress_text: str = ""
    error: str = ""
    result_data: object = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class _QueueItem:
    task_id: str
    func: Callable[..., object]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


class _TaskProgress:
    def __init__(self, info: TaskInfo, total: int, notify: Callable[[], None]) -> None:
        self._info = info
        self._total = max(total, 1)
        self._current = 0
        self._notify = notify

    def update(self, n: int = 1) -> None:
        self._current += n
        self._info.progress = self._current / self._total
        self._notify()

    def set_postfix(self, text: str) -> None:
        self._info.progress_text = text
        self._notify()

    def close(self) -> None:
        self._info.progress = 1.0
        self._notify()


def _exception_message(exc: BaseException) -> str:
    return str(exc).strip() or exc.__class__.__name__


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskInfo] = {}
        self._order: list[str] = []
        self._queue: asyncio.Queue[_QueueItem] = asyncio.Queue()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._worker_task: asyncio.Task[None] | None = None
        self._counter = 0
        self._session_id = uuid4().hex[:8]
        self._subscribers: dict[int, TaskSubscriber] = {}
        self._next_subscriber_id = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._closing = False

    @property
    def tasks(self) -> list[TaskInfo]:
        return [self._tasks[tid] for tid in reversed(self._order)]

    def get(self, task_id: str) -> TaskInfo | None:
        return self._tasks.get(task_id)

    async def close(self) -> None:
        """停止接收新任务，等待队列完成后释放工作线程。"""
        self._closing = True
        try:
            if self._worker_task is not None:
                await self._worker_task
        finally:
            await asyncio.to_thread(self._executor.shutdown, wait=True)
            self._subscribers.clear()

    def subscribe(self, callback: TaskSubscriber) -> Callable[[], None]:
        self._next_subscriber_id += 1
        subscriber_id = self._next_subscriber_id
        self._subscribers[subscriber_id] = callback

        def unsubscribe() -> None:
            self._subscribers.pop(subscriber_id, None)

        return unsubscribe

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is not None:
            return self._loop
        self._loop = asyncio.get_running_loop()
        return self._loop

    def submit(
        self,
        name: str,
        func: Callable[..., object],
        *args: Any,
        kind: str,
        **kwargs: Any,
    ) -> str:
        if self._closing:
            raise RuntimeError("任务队列正在关闭")
        loop = self._ensure_loop()
        self._loop = loop
        self._counter += 1
        task_id = f"{self._session_id}-{self._counter:04d}"
        info = TaskInfo(id=task_id, name=name, kind=kind)
        self._tasks[task_id] = info
        self._order.append(task_id)
        self._queue.put_nowait(_QueueItem(task_id, func, args, kwargs))
        self._dispatch_event()
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = loop.create_task(self._worker())
        return task_id

    def clear_completed(self) -> None:
        to_remove = [tid for tid, t in self._tasks.items() if t.status in ("completed", "failed")]
        for tid in to_remove:
            del self._tasks[tid]
            self._order.remove(tid)
        self._dispatch_event()

    async def _worker(self) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            info = self._tasks[item.task_id]
            info.status = "running"
            self._dispatch_event()

            try:
                sig = inspect.signature(item.func)
                if "make_progress" in sig.parameters:

                    def _make_factory(ti: TaskInfo) -> Callable[[int, str], ProgressReporter]:
                        def factory(total: int, desc: str) -> ProgressReporter:
                            ti.progress_desc = desc
                            ti.progress = 0.0
                            ti.progress_text = ""
                            self._dispatch_event()
                            return _TaskProgress(ti, total, self._dispatch_event)

                        return factory

                    item.kwargs["make_progress"] = _make_factory(info)

                loop = asyncio.get_running_loop()
                info.result_data = await loop.run_in_executor(
                    self._executor, partial(item.func, *item.args, **item.kwargs)
                )
                info.status = "completed"
                info.progress = 1.0
                self._dispatch_event()
            except Exception as e:
                info.status = "failed"
                info.error = _exception_message(e)
                self._dispatch_event()

    def _dispatch_event(self) -> None:
        if self._loop is None:
            self._emit_event()
            return

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is self._loop:
            self._emit_event()
        else:
            self._loop.call_soon_threadsafe(self._emit_event)

    def _emit_event(self) -> None:
        for callback in list(self._subscribers.values()):
            try:
                callback()
            except Exception:
                continue
