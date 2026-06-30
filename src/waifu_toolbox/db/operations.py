import re
import shutil
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np

from ..utils.progress import ProgressFactory, tqdm_factory
from ..utils.result import Result
from .connection import open_connection
from .repo import ImageRepo

_VALID_NAME = re.compile(r"^[A-Za-z0-9_]+$")


def check_name(name: str) -> Result[None] | None:
    """
    检查仓库命名是否合法，仅允许 ASCII 字母、数字和下划线，且不能为空。

    Returns:
        None: 合法
        Result(False, "错误信息"): 不合法
    """
    if not name:
        return Result(False, "名称不能为空")
    if not _VALID_NAME.match(name):
        return Result(False, f"名称 '{name}' 不合法，仅允许 ASCII 字母、数字和下划线")
    return None


@dataclass
class ImageInfo:
    relative_path: str
    label: str


@dataclass
class RepoImages:
    repo_path: Path
    images: List[ImageInfo]


def get_repo_images(repo_name: str) -> RepoImages | None:
    """返回仓库图片列表，仓库不存在时返回 None"""
    with closing(open_connection()) as conn:
        db = ImageRepo(conn)
        if not db.load(repo_name):
            return None
        assert db.repo_path is not None
        images = [ImageInfo(relative_path=rp, label=lb) for rp, lb in zip(db.relative_paths, db.labels)]
        return RepoImages(repo_path=db.repo_path, images=images)


def create_repo(
    repo_name: str,
    path: Path,
    extract_ccip: bool = False,
    extract_dreamsim: bool = False,
    *,
    make_progress: ProgressFactory | None = None,
) -> Result[None]:
    if err := check_name(repo_name):
        return err
    with closing(open_connection()) as conn:
        if conn.execute("""SELECT 1 FROM repos WHERE name = ?""", (repo_name,)).fetchone():
            return Result(False, f"仓库 '{repo_name}' 已存在")

        db = ImageRepo(conn)
        scan = db.scan_init(
            repo_name, path, extract_ccip=extract_ccip, extract_dreamsim=extract_dreamsim, make_progress=make_progress
        )
        if not scan.ok:
            return Result(False, f"仓库 '{repo_name}' 初始化失败（未找到图片）")
        db.save()
        message = f"仓库 '{repo_name}' 创建成功"
        if scan.label_mismatches:
            message += f"\n\n标签冲突（同 hash 不同标签，仅保留首次出现）:\n"
            message += "\n".join(f"  {m}" for m in scan.label_mismatches)
        return Result(True, message)


def rename_repo(repo_name: str, new_name: str) -> Result[None]:
    if err := check_name(new_name):
        return err
    with closing(open_connection()) as conn:
        if conn.execute("""SELECT 1 FROM repos WHERE name = ?""", (new_name,)).fetchone():
            return Result(False, f"名称 '{new_name}' 已被使用")
        with conn:
            result = conn.execute(
                """UPDATE repos SET name = ? WHERE name = ?""",
                (new_name, repo_name),
            )
            if result.rowcount > 0:
                return Result(True, f"已重命名为 '{new_name}'")
            return Result(False, f"仓库 '{repo_name}' 不存在")


def delete_repo(repo_name: str) -> Result[None]:
    with closing(open_connection()) as conn:
        with conn:
            result = conn.execute(
                """DELETE FROM repos WHERE name = ?""",
                (repo_name,),
            )
            if result.rowcount > 0:
                return Result(True, f"已删除仓库 '{repo_name}' 的索引（未删除磁盘文件）")
            return Result(False, f"仓库 '{repo_name}' 不存在")


@dataclass
class RepoSummary:
    name: str
    path: str


def list_repos() -> List[RepoSummary]:
    with closing(open_connection()) as conn:
        rows = conn.execute("""SELECT name, path FROM repos ORDER BY name""").fetchall()
        return [RepoSummary(name=name, path=path) for name, path in rows]


def change_repo_path(repo_name: str, new_path: Path) -> Result[None]:
    with closing(open_connection()) as conn:
        with conn:
            result = conn.execute(
                """UPDATE repos SET path = ? WHERE name = ?""",
                (str(new_path), repo_name),
            )
            if result.rowcount > 0:
                return Result(True, "路径已更新")
            return Result(False, f"仓库 '{repo_name}' 不存在")


def deduplicate_repo(
    repo_name: str, *, make_progress: ProgressFactory | None = None
) -> Result[ImageRepo.DeduplicateResult]:
    with closing(open_connection()) as conn:
        db = ImageRepo(conn)
        if not db.load(repo_name):
            return Result(False, f"仓库 '{repo_name}' 不存在")
        data = db.deduplicate(repo_name, make_progress=make_progress)
        parts: list[str] = []
        if data.deleted > 0:
            parts.append(f"删除了 {data.deleted} 张重复图片")
        if data.label_mismatches:
            parts.append(f"{len(data.label_mismatches)} 条标签不一致")
        message = "、".join(parts) if parts else "未发现重复"
        return Result(True, message, data)


def update_repo(
    repo_name: str,
    extract_ccip: bool = False,
    extract_dreamsim: bool = False,
    *,
    make_progress: ProgressFactory | None = None,
) -> Result[ImageRepo.UpdateResult]:
    with closing(open_connection()) as conn:
        db = ImageRepo(conn)
        if not db.load(repo_name):
            return Result(False, f"仓库 '{repo_name}' 不存在")
        data = db.update(
            repo_name, extract_ccip=extract_ccip, extract_dreamsim=extract_dreamsim, make_progress=make_progress
        )
        if data.new_images or data.updated_labels:
            message = f"新增 {data.new_images} 张图片，更新 {data.updated_labels} 个标签"
        else:
            message = "仓库已是最新"
        return Result(True, message, data)


def purge_repo(repo_name: str, *, make_progress: ProgressFactory | None = None) -> Result[int]:
    with closing(open_connection()) as conn:
        db = ImageRepo(conn)
        if not db.load(repo_name):
            return Result(False, f"仓库 '{repo_name}' 不存在")
        removed = db.purge(repo_name, make_progress=make_progress)
        if removed > 0:
            message = f"清除了 {removed} 条失效记录"
        else:
            message = "没有需要清除的记录"
        return Result(True, message, removed)


@dataclass
class RepoInfo:
    name: str
    path: str
    total_images: int
    label_count: int
    ccip_count: int
    dreamsim_count: int


def _repo_infos_query(repo_name: str | None = None) -> tuple[str, tuple[str, ...]]:
    sql = """
        SELECT
            r.name,
            r.path,
            COUNT(i.hash) AS total_images,
            COUNT(DISTINCT i.label) AS label_count,
            COUNT(i.ccip_feature) AS ccip_count,
            COUNT(i.dreamsim_feature) AS dreamsim_count
        FROM repos AS r
        LEFT JOIN images AS i ON i.repo_id = r.repo_id
    """
    params: tuple[str, ...] = ()
    if repo_name is not None:
        sql += " WHERE r.name = ?"
        params = (repo_name,)
    sql += """
        GROUP BY r.repo_id, r.name, r.path
        ORDER BY r.name
    """
    return sql, params


def _row_to_repo_info(row: tuple[str, str, int, int, int, int]) -> RepoInfo:
    return RepoInfo(
        name=row[0],
        path=row[1],
        total_images=row[2],
        label_count=row[3],
        ccip_count=row[4],
        dreamsim_count=row[5],
    )


def list_repo_infos() -> List[RepoInfo]:
    with closing(open_connection()) as conn:
        sql, params = _repo_infos_query()
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_repo_info(row) for row in rows]


def get_repo_info(repo_name: str) -> RepoInfo | None:
    with closing(open_connection()) as conn:
        sql, params = _repo_infos_query(repo_name)
        row = conn.execute(sql, params).fetchone()
        if row is None:
            return None
        return _row_to_repo_info(row)


@dataclass
class CacheClearResult:
    ccip_deleted: int
    dreamsim_deleted: int


def clear_cache(ccip: bool = False, dreamsim: bool = False) -> Result[CacheClearResult]:
    """清空特征缓存；两个 flag 均不传时清空全部。"""
    with closing(open_connection()) as conn:
        ccip_count = 0
        dreamsim_count = 0

        clear_all = not ccip and not dreamsim

        if clear_all or ccip:
            ccip_count = conn.execute(
                """SELECT COUNT(*) FROM feature_cache WHERE feature_type = ?""",
                ("ccip",),
            ).fetchone()[0]
            with conn:
                conn.execute(
                    """DELETE FROM feature_cache WHERE feature_type = ?""",
                    ("ccip",),
                )

        if clear_all or dreamsim:
            dreamsim_count = conn.execute(
                """SELECT COUNT(*) FROM feature_cache WHERE feature_type = ?""",
                ("dreamsim",),
            ).fetchone()[0]
            with conn:
                conn.execute(
                    """DELETE FROM feature_cache WHERE feature_type = ?""",
                    ("dreamsim",),
                )

        data = CacheClearResult(ccip_deleted=ccip_count, dreamsim_deleted=dreamsim_count)
        total = ccip_count + dreamsim_count
        parts: list[str] = []
        if clear_all or ccip:
            parts.append(f"CCIP {ccip_count} 条")
        if clear_all or dreamsim:
            parts.append(f"DreamSim {dreamsim_count} 条")
        message = f"已清空缓存（{'、'.join(parts)}，共 {total} 条）"
        return Result(True, message, data)


@dataclass
class SearchResult:
    rank: int
    path: str
    label: str
    similarity: float


def search_similar(
    repo_name: str, query_image: Path, top_k: int = 10, skip_update: bool = False
) -> Result[List[SearchResult]]:
    from ..utils.dreamsim import extract_dreamsim_embedding_from_path

    with closing(open_connection()) as conn:
        db = ImageRepo(conn)
        if not db.load(repo_name):
            return Result(False, f"仓库 '{repo_name}' 不存在")
        if not skip_update:
            db.update(repo_name, extract_ccip=False, extract_dreamsim=True)
        db.load_features(dreamsim=True)

        if db.dreamsim_features is None or len(db.dreamsim_features) == 0:
            return Result(False, f"仓库 '{repo_name}' 中没有 DreamSim 特征，请先运行 repo update --dreamsim")

        query_embedding = extract_dreamsim_embedding_from_path(query_image)
        similarities = db.dreamsim_features @ query_embedding
        top_k = min(top_k, len(similarities))
        top_indices = np.argsort(similarities)[::-1][:top_k]

        if db.repo_path is None:
            return Result(False, f"仓库 '{repo_name}' 路径不可用")
        results: List[SearchResult] = []
        for rank, idx in enumerate(top_indices, 1):
            idx: int
            rel_path = db.relative_paths[idx]
            full_path = str(db.repo_path / rel_path) if rel_path else "N/A"
            results.append(
                SearchResult(
                    rank=rank,
                    path=full_path,
                    label=db.labels[idx],
                    similarity=float(similarities[idx]),
                )
            )

        return Result(True, f"找到 {len(results)} 条结果", results)


def flatten_repo(repo_name: str, *, make_progress: ProgressFactory | None = None) -> Result[Path]:
    with closing(open_connection()) as conn:
        db = ImageRepo(conn)
        if not db.load(repo_name):
            return Result(False, f"仓库 '{repo_name}' 不存在")

        repo_root = db.repo_path
        assert repo_root is not None

        if not repo_root.exists():
            return Result(False, f"仓库路径不存在: {repo_root}")

        flat_dir = repo_root.parent / f"_{repo_name}_flat"
        if flat_dir.exists():
            shutil.rmtree(flat_dir)
        flat_dir.mkdir(exist_ok=True)

        factory = make_progress or tqdm_factory
        sub_folders = [d for d in repo_root.iterdir() if d.is_dir()]
        bar = factory(len(sub_folders), "扁平化文件夹")

        for item in sub_folders:
            for file in item.rglob("*"):
                if file.is_file():
                    rel_path = file.relative_to(repo_root)
                    target_dir = flat_dir / rel_path.parts[0]
                    target_dir.mkdir(exist_ok=True)

                    target_file = target_dir / file.name
                    if target_file.exists():
                        bar.close()
                        return Result(False, f"发现重复的文件名: {target_file.name}，请先手动处理")

                    shutil.copy2(file, target_file)
            bar.update(1)

        bar.close()
        return Result(True, f"输出文件夹: {flat_dir}", flat_dir)
