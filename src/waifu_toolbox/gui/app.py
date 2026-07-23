# pyright: reportUnknownMemberType=false
import base64
import mimetypes
import random
from collections.abc import Callable
from ipaddress import IPv4Address, IPv4Network, IPv6Address, ip_address
from pathlib import Path
from typing import Any

from nicegui import app, context, ui
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .components.layout import render_shell
from .context import GuiContext
from .pages import (
    classify,
    convert,
    dashboard,
    repo_detail,
    search,
    settings,
    sort,
    tasks,
)
from .utils.storage import save as storage_save

_access_guard_installed = False
_static_assets_mounted = False
_ALLOWED_LAN = IPv4Network("192.168.0.0/16")


class _LocalNetworkOnlyMiddleware:
    def __init__(self, app_instance: ASGIApp) -> None:
        self.app = app_instance

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_host = client[0] if client is not None else None
        if _is_allowed_client_host(client_host):
            await self.app(scope, receive, send)
            return

        if scope["type"] == "http":
            response = PlainTextResponse("Access denied.", status_code=403)
            await response(scope, receive, send)
            return

        await send({"type": "websocket.close", "code": 1008})


def _is_allowed_client_host(host: str | None) -> bool:
    if host is None:
        return False

    try:
        client_ip = ip_address(host)
    except ValueError:
        return False

    if isinstance(client_ip, IPv6Address) and client_ip.ipv4_mapped is not None:
        client_ip = client_ip.ipv4_mapped

    return client_ip.is_loopback or (isinstance(client_ip, IPv4Address) and client_ip in _ALLOWED_LAN)


def _install_access_guard() -> None:
    global _access_guard_installed

    if _access_guard_installed:
        return

    app.add_middleware(_LocalNetworkOnlyMiddleware)
    _access_guard_installed = True


def _mount_static_assets(assets_dir: Path) -> None:
    global _static_assets_mounted

    if _static_assets_mounted:
        return

    app.add_static_files("/assets", assets_dir)
    _static_assets_mounted = True


def _build_root(routes: dict[str, Callable[..., Any]]) -> Callable[[], None]:
    def root() -> None:
        gui_ctx = GuiContext()
        context.client.on_disconnect(gui_ctx.cleanup)
        render_shell(gui_ctx, routes)

    return root


def run(dev: bool = False) -> None:
    assets_dir = Path(__file__).with_name("assets")
    _mount_static_assets(assets_dir)

    # 将目标 favicon 编码为 data URI，否则 NiceGUI 会自动将其转换为固定的 /favicon.ico 路径，导致浏览器错误缓存
    favicon_path = random.choice(list((assets_dir / "favicons").glob("*.png")))
    mime_type = mimetypes.guess_type(favicon_path.name)[0] or "image/png"
    favicon_data = base64.b64encode(favicon_path.read_bytes()).decode("ascii")
    favicon = f"data:{mime_type};base64,{favicon_data}"

    _install_access_guard()
    routes = {
        "/": dashboard.render,
        "/repo/{repo_name}": repo_detail.render,
        "/classify": classify.render,
        "/sort": sort.render,
        "/convert": convert.render,
        "/search": search.render,
        "/tasks": tasks.render,
        "/settings": settings.render,
    }
    app.on_shutdown(storage_save)
    ui.run(
        root=_build_root(routes),
        title="Waifu Toolbox",
        host="0.0.0.0",
        port=3039,
        favicon=favicon,
        reload=dev,
        dark=False,
    )
