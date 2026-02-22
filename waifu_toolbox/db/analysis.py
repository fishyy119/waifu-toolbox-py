from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Literal

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
    def from_files(cls, files: list[Path]) -> "FileStat":
        return cls(count=len(files), size=sum(f.stat().st_size for f in files))


def print_stats(stats: Dict[str, FileStat], title: str = "Statistics") -> None:
    console = Console()
    table = Table(title=title, box=box.SIMPLE_HEAVY, show_lines=False)

    table.add_column("Type", justify="left")
    table.add_column("Count", justify="right")
    table.add_column("Count %", justify="right")
    table.add_column("Size (MB)", justify="right")
    table.add_column("Size %", justify="right")

    total_count = sum(stat.count for stat in stats.values())
    total_size = sum(stat.size for stat in stats.values())

    for key, stat in stats.items():
        size_mb = stat.size / (1024 * 1024)
        count_ratio = stat.count / total_count if total_count else 0
        size_ratio = stat.size / total_size if total_size else 0

        table.add_row(key, f"{stat.count}", f"{count_ratio:.2%}", f"{size_mb:.2f}", f"{size_ratio:.2%}")

    console.print(table)


def analyze_repo(repo_name: str, type: Literal["_extension", "_category"] | str = "_extension") -> None:
    """
    type:
        - "_extension": 按文件扩展名统计（保留符）
        - "_category": 按一级子目录统计（保留符）
        - 其他字符串：按指定子目录统计（可以任意拼接期望的子目录）
    """
    # 虽然归属到 repo 命令下，但它只利用里面存储的仓库路径信息，不涉及数据库操作
    db = ImageDBCCIP()
    db.load(repo_name)
    repo_root = db.repo_path
    assert repo_root is not None

    stats: Dict[str, FileStat] = {}
    if type == "_extension":
        for ext in IMG_EXTS:
            ext_files = list(repo_root.rglob(ext))
            stat = FileStat.from_files(ext_files)
            stats[ext] = stat

    elif type == "_category":
        for category in repo_root.iterdir():
            if category.is_dir():
                cat_files = list(category.rglob("*"))
                stat = FileStat.from_files(cat_files)
                stats[category.name] = stat

    else:
        new_root = repo_root / type
        if new_root.exists() and new_root.is_dir():
            for ext in IMG_EXTS:
                ext_files = list(new_root.rglob(ext))
                stat = FileStat.from_files(ext_files)
                stats[ext] = stat
        else:
            log_error(f"Directory {new_root} does not exist")
            exit(1)

    print_stats(stats, title=f"Repository Analysis: {repo_name} ({type})")
