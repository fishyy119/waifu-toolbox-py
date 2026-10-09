import logging
import os
import socket
import webbrowser
from collections.abc import AsyncGenerator, Sequence
from contextlib import ExitStack, asynccontextmanager, suppress
from pathlib import Path
from threading import Timer

import uvicorn
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse, JSONResponse, Response

from ..core.errors import OperationError
from .api.models import ErrorDetail, ErrorResponse
from .api.routes import router
from .services.task_manager import TaskManager


def create_app() -> FastAPI:
    """提供业务 API，并托管构建后的 Vue SPA。"""
    frontend = Path(__file__).resolve().parents[1] / "frontend"

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        manager = TaskManager()
        application.state.tasks = manager
        try:
            yield
        finally:
            await manager.close()

    application = FastAPI(
        title="Waifu Toolbox API",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )

    async def http_error(_request: Request, error: HTTPException) -> JSONResponse:
        body = ErrorResponse(error=ErrorDetail(code="http_error", message=str(error.detail)))
        return JSONResponse(body.model_dump(mode="json"), status_code=error.status_code)

    async def operation_error(_request: Request, error: OperationError) -> JSONResponse:
        body = ErrorResponse(error=ErrorDetail(code="operation_failed", message=str(error)))
        return JSONResponse(body.model_dump(mode="json"), status_code=400)

    async def invalid_request(_request: Request, error: RequestValidationError) -> JSONResponse:
        body = ErrorResponse(
            error=ErrorDetail(
                code="validation_error", message="请求参数不符合要求", details=jsonable_encoder(error.errors())
            )
        )
        return JSONResponse(body.model_dump(mode="json"), status_code=422)

    application.exception_handler(HTTPException)(http_error)
    application.exception_handler(OperationError)(operation_error)
    application.exception_handler(RequestValidationError)(invalid_request)
    application.include_router(router)

    def spa(full_path: str) -> Response:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(404, "API 接口不存在")
        requested = (frontend / full_path).resolve()
        if requested.is_relative_to(frontend) and requested.is_file():
            return FileResponse(requested)
        if full_path.startswith("assets/") or Path(full_path).suffix:
            raise HTTPException(404, "静态资源不存在")
        index = frontend / "index.html"
        if index.is_file():
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
        raise HTTPException(503, "前端资源尚未构建，请在项目目录执行 pnpm build")

    application.add_api_route("/{full_path:path}", spa, methods=["GET"], include_in_schema=False)
    return application


def run(*, additional_hosts: Sequence[str] = (), port: int = 3039) -> None:
    """始终监听回环地址，并追加用户显式指定的网卡地址。"""
    hosts = tuple(dict.fromkeys(("127.0.0.1", *additional_hosts)))
    config = uvicorn.Config("waifu_toolbox.gui.app:create_app", factory=True, host="127.0.0.1", port=port, workers=1)
    server = uvicorn.Server(config)
    logger = logging.getLogger("uvicorn.error")
    with ExitStack() as cleanup:
        listeners: list[socket.socket] = []
        try:
            for host in hosts:
                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cleanup.callback(listener.close)
                # Windows 使用独占绑定，其他平台允许服务重启时复用地址。
                option = socket.SO_EXCLUSIVEADDRUSE if os.name == "nt" else socket.SO_REUSEADDR
                listener.setsockopt(socket.SOL_SOCKET, option, 1)
                listener.bind((host, port))
                listener.set_inheritable(True)
                listeners.append(listener)
        except OSError as error:
            logger.error("无法监听指定地址: %s", error)
            raise SystemExit(3) from None
        for host in hosts:
            logger.info("Uvicorn running on http://%s:%d (Press CTRL+C to quit)", host, port)
        browser = Timer(1, webbrowser.open, args=(f"http://127.0.0.1:{port}",))
        browser.daemon = True
        browser.start()
        with suppress(KeyboardInterrupt):
            server.run(sockets=listeners)
    if not server.started:
        raise SystemExit(3)
