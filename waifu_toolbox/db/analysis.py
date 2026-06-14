from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal

from .connection import open_connection
from ..utils.image import IMG_EXTS
from ..utils.result import Result
from .repo import ImageRepo


@dataclass
class FileStat:
    count: int = 0
    size: int = 0

    @classmethod
    def from_files(cls, files: List[Path]) -> "FileStat":
        return cls(count=len(files), size=sum(f.stat().st_size for f in files))


def analyze_repo(
    repo_name: str,
    type: Literal["extension", "category"] = "extension",
    target: str = "",
) -> Result[Dict[str, FileStat]]:
    """返回 {键: FileStat} 映射。键为扩展名或类别名。"""
    with closing(open_connection()) as conn:
        db = ImageRepo(conn)
        if not db.load(repo_name):
            return Result(False, f"仓库 '{repo_name}' 不存在")

        repo_root = db.repo_path
        assert repo_root is not None

        analyze_root = repo_root / target if target else repo_root
        if not (analyze_root.exists() and analyze_root.is_dir()):
            return Result(False, f"目录不存在: {analyze_root}")

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

        return Result(True, "分析完成", stats)
