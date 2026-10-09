import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..db import operations as storage
from ..db.models import CacheClearResult, RepoImages, RepoInfo, RepoSummary
from ..utils.progress import ProgressFactory, tqdm_factory
from .errors import OperationError
from .repository import ImageRepo

_VALID_NAME = re.compile(r"^[A-Za-z0-9_]+$")


def check_name(name: str) -> None:
    """
    检查仓库命名是否合法，仅允许 ASCII 字母、数字和下划线，且不能为空。

    Raises:
        OperationError: 名称不合法。
    """
    if not name:
        raise OperationError("名称不能为空")
    if not _VALID_NAME.match(name):
        raise OperationError(f"名称 '{name}' 不合法，仅允许 ASCII 字母、数字和下划线")


@dataclass
class SearchResult:
    rank: int
    path: str
    label: str
    similarity: float


def get_repo_images(repo_name: str) -> RepoImages | None:
    return storage.get_repo_images(repo_name)


def list_repos() -> list[RepoSummary]:
    return storage.list_repos()


def list_repo_infos() -> list[RepoInfo]:
    return storage.list_repo_infos()


def get_repo_info(repo_name: str) -> RepoInfo | None:
    return storage.get_repo_info(repo_name)


def create_repo(
    repo_name: str,
    path: Path,
    extract_ccip: bool = False,
    extract_dreamsim: bool = False,
    *,
    make_progress: ProgressFactory | None = None,
) -> ImageRepo.ScanInitResult:
    check_name(repo_name)
    if storage.repo_exists(repo_name):
        raise OperationError(f"仓库 '{repo_name}' 已存在")

    db = ImageRepo()
    scan = db.scan_init(
        repo_name, path, extract_ccip=extract_ccip, extract_dreamsim=extract_dreamsim, make_progress=make_progress
    )
    if not scan.ok:
        raise OperationError(f"仓库 '{repo_name}' 初始化失败（未找到图片）")
    if not db.save(create_only=True):
        raise OperationError(f"仓库 '{repo_name}' 已存在")
    return scan


def deduplicate_repo(
    repo_name: str,
    *,
    make_progress: ProgressFactory | None = None,
) -> ImageRepo.DeduplicateResult:
    db = ImageRepo()
    if not db.load(repo_name):
        raise OperationError(f"仓库 '{repo_name}' 不存在")
    return db.deduplicate(repo_name, make_progress=make_progress)


def update_repo(
    repo_name: str,
    extract_ccip: bool = False,
    extract_dreamsim: bool = False,
    *,
    make_progress: ProgressFactory | None = None,
) -> ImageRepo.UpdateResult:
    db = ImageRepo()
    if not db.load(repo_name):
        raise OperationError(f"仓库 '{repo_name}' 不存在")
    return db.update(
        repo_name, extract_ccip=extract_ccip, extract_dreamsim=extract_dreamsim, make_progress=make_progress
    )


def purge_repo(repo_name: str, *, make_progress: ProgressFactory | None = None) -> int:
    db = ImageRepo()
    if not db.load(repo_name):
        raise OperationError(f"仓库 '{repo_name}' 不存在")
    return db.purge(repo_name, make_progress=make_progress)


def search_similar(
    repo_name: str,
    query_image: Path,
    top_k: int = 10,
    skip_update: bool = False,
) -> list[SearchResult]:
    from ..utils.dreamsim import extract_dreamsim_embedding_from_path

    db = ImageRepo()
    if not db.load(repo_name):
        raise OperationError(f"仓库 '{repo_name}' 不存在")
    if not skip_update:
        db.update(repo_name, extract_ccip=False, extract_dreamsim=True)
    db.load_features(dreamsim=True)

    if db.dreamsim_features is None or len(db.dreamsim_features) == 0:
        raise OperationError(f"仓库 '{repo_name}' 中没有 DreamSim 特征，请先提取")

    query_embedding = extract_dreamsim_embedding_from_path(query_image)
    similarities = db.dreamsim_features @ query_embedding
    top_k = min(top_k, len(similarities))
    top_indices = np.argsort(similarities)[::-1][:top_k]

    if db.repo_path is None:
        raise OperationError(f"仓库 '{repo_name}' 路径不可用")
    results: list[SearchResult] = []
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

    return results


def flatten_repo(repo_name: str, *, make_progress: ProgressFactory | None = None) -> Path:
    db = ImageRepo()
    if not db.load(repo_name):
        raise OperationError(f"仓库 '{repo_name}' 不存在")

    repo_root = db.repo_path
    assert repo_root is not None

    if not repo_root.exists():
        raise OperationError(f"仓库路径不存在: {repo_root}")

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
                    raise OperationError(f"发现重复的文件名: {target_file.name}，请先手动处理")

                shutil.copy2(file, target_file)
        bar.update(1)

    bar.close()
    return flat_dir


def rename_repo(repo_name: str, new_name: str) -> None:
    check_name(new_name)
    if storage.repo_exists(new_name):
        raise OperationError(f"名称 '{new_name}' 已被使用")
    if not storage.rename_repo(repo_name, new_name):
        raise OperationError(f"仓库 '{repo_name}' 不存在")


def delete_repo(repo_name: str) -> None:
    if not storage.delete_repo(repo_name):
        raise OperationError(f"仓库 '{repo_name}' 不存在")


def change_repo_path(repo_name: str, new_path: Path) -> None:
    if not storage.change_repo_path(repo_name, str(new_path)):
        raise OperationError(f"仓库 '{repo_name}' 不存在")


def clear_cache(ccip: bool = False, dreamsim: bool = False) -> CacheClearResult:
    """清空特征缓存；两个 flag 均不传时清空全部。"""
    clear_all = not ccip and not dreamsim
    return storage.clear_cache(clear_all or ccip, clear_all or dreamsim)
