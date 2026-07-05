from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict

from nicegui import ui

_ASSETS_DIR = Path(__file__).parent.parent / "assets"
DIRECTORY_TREE_CSS = (_ASSETS_DIR / "directory_tree.css").read_text(encoding="utf-8")

_directory_tree_assets_ready = False


class DirectoryTreeNode(TypedDict):
    id: str
    label: str
    children: list["DirectoryTreeNode"]


@dataclass
class DirectoryTreeState:
    selected_key: str
    expanded_keys: set[str] = field(default_factory=lambda: _new_expanded_keys(), repr=False)


def _new_expanded_keys() -> set[str]:
    return set()


def _ensure_directory_tree_assets() -> None:
    global _directory_tree_assets_ready
    if _directory_tree_assets_ready:
        return
    ui.add_css(DIRECTORY_TREE_CSS, shared=True)
    _directory_tree_assets_ready = True


def directory_tree(
    *,
    nodes: Sequence[DirectoryTreeNode],
    state: DirectoryTreeState,
    on_selection_change: Callable[[str], None] | None = None,
) -> None:
    _ensure_directory_tree_assets()

    def handle_node_click(key: str, expandable: bool) -> None:
        previous_key = state.selected_key
        state.selected_key = key
        if expandable:
            if key in state.expanded_keys:
                state.expanded_keys.remove(key)
            else:
                state.expanded_keys.add(key)
        if on_selection_change is not None and key != previous_key:
            on_selection_change(key)
        render_tree.refresh()

    @ui.refreshable
    def render_tree() -> None:
        with ui.column().classes("w-full repo-directory-tree"):
            _render_nodes(
                nodes=nodes,
                selected_key=state.selected_key,
                expanded_keys=state.expanded_keys,
                on_node_click=handle_node_click,
                depth=0,
            )

    render_tree()


def _render_nodes(
    *,
    nodes: Sequence[DirectoryTreeNode],
    selected_key: str,
    expanded_keys: Collection[str],
    on_node_click: Callable[[str, bool], None],
    depth: int,
) -> None:
    for node in nodes:
        key = node["id"]
        expandable = bool(node["children"])
        expanded = key in expanded_keys
        selected = key == selected_key
        indent_rem = 0.25 + depth * 0.75

        row_classes = "w-full items-center no-wrap repo-directory-tree-node"
        if selected:
            row_classes += " repo-directory-tree-node-selected"

        with ui.column().classes("w-full gap-0"):
            row = (
                ui.row()
                .classes(row_classes)
                .style(f"padding-left: {indent_rem}rem;")
                .on(
                    "click",
                    lambda _, current_key=key, current_expandable=expandable: on_node_click(
                        current_key, current_expandable
                    ),
                )
            )
            with row:
                if expandable:
                    ui.icon("expand_more" if expanded else "chevron_right").classes(
                        "repo-directory-tree-icon text-base"
                    )
                else:
                    ui.element("div").classes("repo-directory-tree-icon")
                ui.label(node["label"]).classes("text-sm truncate min-w-0")

            if expandable and expanded:
                _render_nodes(
                    nodes=node["children"],
                    selected_key=selected_key,
                    expanded_keys=expanded_keys,
                    on_node_click=on_node_click,
                    depth=depth + 1,
                )
