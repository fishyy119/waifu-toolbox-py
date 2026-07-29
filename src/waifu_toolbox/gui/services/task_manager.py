import asyncio
import inspect
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from typing import Any, Literal, TypeVar, cast

from ...utils.progress import ProgressReporter
from ...utils.result import Result

T = TypeVar("T")
TaskEventType = Literal["created", "started", "progress", "completed", "failed", "cleared"]
TaskSubscriber = Callable[["TaskEvent"], None]


@dataclass
class TaskInfo:
    id: str
    name: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    progress: float = 0.0
    progress_desc: str = ""
    progress_text: str = ""
    result_text: str = ""
    error: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class TaskEvent:
    type: TaskEventType
    task_id: str | None = None
    task: TaskInfo | None = None


@dataclass
class _QueueItem:
    task_id: str
    func: Callable[..., Any]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    format_result: Callable[[Any], str] | None = None
    waiter: asyncio.Future[Any] | None = None


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
        self._subscribers: dict[int, TaskSubscriber] = {}
        self._next_subscriber_id = 0
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def tasks(self) -> list[TaskInfo]:
        return [self._tasks[tid] for tid in reversed(self._order)]

    @property
    def active_count(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status in ("pending", "running"))

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

    def _enqueue(
        self,
        name: str,
        func: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        format_result: Callable[[Any], str] | None,
        waiter: asyncio.Future[Any] | None = None,
    ) -> str:
        loop = self._ensure_loop()
        self._loop = loop
        self._counter += 1
        task_id = f"{self._counter:04d}"
        info = TaskInfo(id=task_id, name=name)
        self._tasks[task_id] = info
        self._order.append(task_id)
        self._queue.put_nowait(_QueueItem(task_id, func, args, kwargs, format_result, waiter))
        self._dispatch_event(TaskEvent(type="created", task_id=task_id, task=info))
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = loop.create_task(self._worker())
        return task_id

    def submit(
        self,
        name: str,
        func: Callable[..., T],
        *args: Any,
        format_result: Callable[[T], str] | None = None,
        **kwargs: Any,
    ) -> str:
        return self._enqueue(
            name,
            func,
            tuple(args),
            dict(kwargs),
            cast("Callable[[Any], str] | None", format_result),
        )

    async def run(
        self,
        name: str,
        func: Callable[..., T],
        *args: Any,
        format_result: Callable[[T], str] | None = None,
        **kwargs: Any,
    ) -> T:
        loop = asyncio.get_running_loop()
        self._loop = loop
        waiter: asyncio.Future[T] = loop.create_future()
        self._enqueue(
            name,
            func,
            tuple(args),
            dict(kwargs),
            cast("Callable[[Any], str] | None", format_result),
            cast("asyncio.Future[Any]", waiter),
        )
        return await waiter

    async def run_result(
        self,
        name: str,
        func: Callable[..., Result[T]],
        *args: Any,
        **kwargs: Any,
    ) -> Result[T]:
        try:
            result = await self.run(name, func, *args, **kwargs)
        except Exception as exc:
            return Result(False, _exception_message(exc))
        return result

    def clear_completed(self) -> None:
        to_remove = [tid for tid, t in self._tasks.items() if t.status in ("completed", "failed")]
        for tid in to_remove:
            del self._tasks[tid]
            self._order.remove(tid)
        self._dispatch_event(TaskEvent(type="cleared"))

    async def _worker(self) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            info = self._tasks[item.task_id]
            info.status = "running"
            self._dispatch_event(TaskEvent(type="started", task_id=item.task_id, task=info))

            sig = inspect.signature(item.func)
            if "make_progress" in sig.parameters:

                def _make_factory(ti: TaskInfo) -> Callable[[int, str], ProgressReporter]:
                    def factory(total: int, desc: str) -> ProgressReporter:
                        ti.progress_desc = desc
                        ti.progress = 0.0
                        ti.progress_text = ""
                        self._dispatch_event(TaskEvent(type="progress", task_id=ti.id, task=ti))
                        return _TaskProgress(
                            ti,
                            total,
                            lambda: self._dispatch_event(TaskEvent(type="progress", task_id=ti.id, task=ti)),
                        )

                    return factory

                item.kwargs["make_progress"] = _make_factory(info)

            try:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(self._executor, partial(item.func, *item.args, **item.kwargs))
                if isinstance(result, Result) and not result.ok:
                    info.status = "failed"
                    info.error = result.message
                    self._dispatch_event(TaskEvent(type="failed", task_id=item.task_id, task=info))
                else:
                    info.status = "completed"
                    info.progress = 1.0
                    if isinstance(result, Result):
                        info.result_text = result.message
                    elif item.format_result:
                        try:
                            info.result_text = item.format_result(result)
                        except Exception:
                            info.result_text = str(result) if result is not None else ""
                    self._dispatch_event(TaskEvent(type="completed", task_id=item.task_id, task=info))
                if item.waiter is not None and not item.waiter.done():
                    item.waiter.set_result(result)
            except Exception as e:
                info.status = "failed"
                info.error = _exception_message(e)
                self._dispatch_event(TaskEvent(type="failed", task_id=item.task_id, task=info))
                if item.waiter is not None and not item.waiter.done():
                    item.waiter.set_exception(e)

    def _dispatch_event(self, event: TaskEvent) -> None:
        if self._loop is None:
            self._emit_event(event)
            return

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is self._loop:
            self._emit_event(event)
        else:
            self._loop.call_soon_threadsafe(self._emit_event, event)

    def _emit_event(self, event: TaskEvent) -> None:
        for callback in list(self._subscribers.values()):
            try:
                callback(event)
            except Exception:
                continue


task_manager = TaskManager()
