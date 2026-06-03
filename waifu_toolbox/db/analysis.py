from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal

from rich import box
from rich.console import Console
from rich.table import Table

from ..utils.console import log_error
from ..utils.image import IMG_EXTS
from .ccip_db import ImageDBCCIP


@dataclass
class FileStat:
    count: int = 0
    size: int = 0

    @classmethod
    def from_files(cls, files: List[Path]) -> "FileStat":
        return cls(count=len(files), size=sum(f.stat().st_size for f in files))


@dataclass
class StatRow:
    type_name: str
    count: str
    count_ratio: str
    size_mb: str
    size_ratio: str
    sort_value: float


def print_stats(
    stats: Dict[str, FileStat],
    title: str = "Statistics",
    sort_key: Literal["count", "size", "none"] = "none",
) -> None:
    total_count = sum(stat.count for stat in stats.values())
    total_size = sum(stat.size for stat in stats.values())
    columns: List[StatRow] = []

    for key, stat in stats.items():
        size_mb = stat.size / (1024 * 1024)
        count_ratio = stat.count / total_count if total_count else 0
        size_ratio = stat.size / total_size if total_size else 0
        sort_value = {"count": stat.count, "size": size_mb, "none": 0}[sort_key]

        columns.append(
            StatRow(
                type_name=key,
                count=f"{stat.count}",
                count_ratio=f"{count_ratio:.2%}",
                size_mb=f"{size_mb:.2f}",
                size_ratio=f"{size_ratio:.2%}",
                sort_value=sort_value,
            )
        )

    console = Console()
    table = Table(title=title, box=box.SIMPLE_HEAVY, show_lines=False, show_footer=True)
    table.add_column("Type", justify="left", footer="Total", style="bold")
    table.add_column("Count", justify="right", footer=f"{total_count}")
    table.add_column("Count %", justify="right", footer="100.00%" if total_count else "0.00%")
    table.add_column("Size (MB)", justify="right", footer=f"{total_size / (1024 * 1024):.2f}")
    table.add_column("Size %", justify="right", footer="100.00%" if total_size else "0.00%")

    columns.sort(key=lambda row: row.sort_value, reverse=True)
    for col in columns:
        table.add_row(
            col.type_name,
            col.count,
            col.count_ratio,
            col.size_mb,
            col.size_ratio,
        )

    console.print(table)


def analyze_repo(
    repo_name: str,
    type: Literal["extension", "category"] = "extension",
    target: str = "",
    sort_key: Literal["count", "size", "none"] = "none",
) -> None:
    """
    type:
        - "extension": 按文件扩展名统计（保留符）
        - "category": 按一级子目录统计（保留符）

    target: 根目录或任意拼接的子目录
    """
    # 虽然归属到 repo 命令下，但它只利用里面存储的仓库路径信息，不涉及数据库操作
    db = ImageDBCCIP()
    db.load(repo_name)
    repo_root = db.repo_path
    assert repo_root is not None

    analyze_root = repo_root / target if target else repo_root
    if not (analyze_root.exists() and analyze_root.is_dir()):
        log_error(f"Directory {analyze_root} does not exist or is not a directory")
        exit(1)

    stats: Dict[str, FileStat] = {}
    if type == "extension":
        for ext in IMG_EXTS:
            ext_files = list(analyze_root.rglob(ext))
            stat = FileStat.from_files(ext_files)
            stats[ext] = stat

    elif type == "category":
        for category in analyze_root.iterdir():
            if category.is_dir():
                cat_files = list(category.rglob("*"))
                stat = FileStat.from_files(cat_files)
                stats[category.name] = stat

    print_stats(
        stats,
        title=f"{type.capitalize()} Analysis: {repo_name}" + (f"/{target}" if target else ""),
        sort_key=sort_key,
    )
