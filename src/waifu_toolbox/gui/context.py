from collections.abc import Callable, Sequence
from dataclasses import dataclass

from nicegui.binding import bindable_dataclass

from .services.task_manager import TaskManager, task_manager
from .utils.storage import prefs

RouteDisposer = Callable[[], None]


@dataclass(frozen=True)
class DrawerPanel:
    key: str
    label: str
    render: Callable[[], None]
    icon: str = "menu"


@dataclass(frozen=True)
class SearchResultEntry:
    label: str
    path: str
    similarity: float


@bindable_dataclass
class ShellState:
    current_path: str = "/"
    panel: str = "navigation"


@bindable_dataclass
class SearchState:
    repo_name: str = ""
    query_path: str = ""
    top_k: int = 10
    skip_update: bool = True
    loading: bool = False
    error: str = ""


class GuiContext:
    def __init__(self, *, tasks: TaskManager = task_manager) -> None:
        """初始化当前客户端的共享 GUI 上下文。"""
        self.prefs = prefs
        self.task_manager = tasks
        self.shell_state = ShellState()
        self.search_state = SearchState()
        self.search_results: list[SearchResultEntry] = []
        self._navigation_panel: DrawerPanel | None = None
        self._drawer_panels: list[DrawerPanel] = []
        self._refresh_drawer: Callable[[], None] | None = None
        self._refresh_header: Callable[[], None] | None = None
        self._route_disposers: list[RouteDisposer] = []

    @property
    def drawer_panels(self) -> tuple[DrawerPanel, ...]:
        """返回当前路由可用的抽屉面板集合。"""
        return tuple(self._drawer_panels)

    @property
    def current_panel(self) -> DrawerPanel | None:
        """解析当前激活的抽屉面板。"""
        for panel in self._drawer_panels:
            if panel.key == self.shell_state.panel:
                return panel
        return self._drawer_panels[0] if self._drawer_panels else None

    def register_shell_callbacks(
        self,
        *,
        refresh_drawer: Callable[[], None],
        refresh_header: Callable[[], None],
    ) -> None:
        """登记壳层刷新回调，供路由切换时触发。"""
        self._refresh_drawer = refresh_drawer
        self._refresh_header = refresh_header

    def set_navigation_panel(self, panel: DrawerPanel) -> None:
        """设置默认导航面板，并在首次初始化时激活它。"""
        self._navigation_panel = panel
        if not self._drawer_panels:
            self._drawer_panels = [panel]
            self.shell_state.panel = panel.key

    def activate_route(
        self,
        path: str,
        *,
        drawer_panels: Sequence[DrawerPanel] = (),
        default_panel: str | None = None,
        include_navigation: bool = True,
    ) -> None:
        """切换到新路由，并更新该路由对应的抽屉配置。"""
        self._dispose_route_resources()
        self.shell_state.current_path = path
        self._set_drawer_panels(
            drawer_panels=drawer_panels,
            default_panel=default_panel,
            include_navigation=include_navigation,
        )
        self._refresh_shell()

    def register_route_disposer(self, disposer: RouteDisposer) -> None:
        """登记页面级清理器，供路由离开或断开连接时执行。"""
        self._route_disposers.append(disposer)

    def toggle_drawer_panel(self) -> None:
        """在当前路由的可用抽屉面板之间循环切换。"""
        if len(self._drawer_panels) <= 1:
            return
        current_index = next(
            (index for index, panel in enumerate(self._drawer_panels) if panel.key == self.shell_state.panel),
            0,
        )
        next_panel = self._drawer_panels[(current_index + 1) % len(self._drawer_panels)]
        self.shell_state.panel = next_panel.key
        self._refresh_shell()

    def cleanup(self) -> None:
        """清理当前客户端尚未释放的页面级资源。"""
        self._dispose_route_resources()

    def _set_drawer_panels(
        self,
        *,
        drawer_panels: Sequence[DrawerPanel],
        default_panel: str | None,
        include_navigation: bool,
    ) -> None:
        """合并导航面板与路由面板，并确定默认激活项。"""
        panels = list(drawer_panels)
        if include_navigation and self._navigation_panel is not None:
            panels.append(self._navigation_panel)
        if not panels and self._navigation_panel is not None:
            panels = [self._navigation_panel]

        self._drawer_panels = panels
        panel_keys = {panel.key for panel in panels}
        if default_panel is not None and default_panel in panel_keys:
            self.shell_state.panel = default_panel
        elif self.shell_state.panel not in panel_keys and panels:
            self.shell_state.panel = panels[0].key

    def _dispose_route_resources(self) -> None:
        """按后进先出顺序执行已登记的页面清理器。"""
        while self._route_disposers:
            disposer = self._route_disposers.pop()
            try:
                disposer()
            except Exception:
                continue

    def _refresh_shell(self) -> None:
        """通知壳层刷新抽屉和头部控件。"""
        if self._refresh_drawer is not None:
            self._refresh_drawer()
        if self._refresh_header is not None:
            self._refresh_header()
