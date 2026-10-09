from collections import Counter
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from ...db.models import ImageInfo
from ..utils.sorting import localized_sort_key


@dataclass
class DirectoryNode:
    key: str
    label: str
    count: int = 0
    children: list["DirectoryNode"] = field(default_factory=lambda: list[DirectoryNode]())


def directory_key(relative_path: str) -> str:
    return PurePosixPath(relative_path.replace("\\", "/")).parent.as_posix()


def build_directory_tree(images: list[ImageInfo]) -> list[DirectoryNode]:
    """按本地化排序构建目录树，数量仅统计目录直属图片。"""
    nodes: dict[str, DirectoryNode] = {}
    roots: list[DirectoryNode] = []
    for image in images:
        parts = PurePosixPath(image.relative_path.replace("\\", "/")).parts[:-1]
        parent: DirectoryNode | None = None
        for depth, part in enumerate(parts):
            key = "/".join(parts[: depth + 1])
            if key not in nodes:
                node = DirectoryNode(key=key, label=part)
                nodes[key] = node
                (parent.children if parent is not None else roots).append(node)
            parent = nodes[key]
        if parent is not None:
            parent.count += 1

    def sort_nodes(branches: list[DirectoryNode]) -> None:
        branches.sort(key=lambda node: localized_sort_key(node.label))
        for node in branches:
            sort_nodes(node.children)

    sort_nodes(roots)
    return roots


def label_distribution(images: list[ImageInfo]) -> list[dict[str, str | int]]:
    counts = Counter(image.label for image in images)
    return [{"label": label, "count": count} for label, count in counts.most_common()]
