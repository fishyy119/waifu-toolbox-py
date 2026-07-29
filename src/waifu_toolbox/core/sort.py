# pyright: standard

import warnings
from contextlib import closing
from pathlib import Path
from typing import cast

import numpy as np
import umap
from numpy.typing import NDArray

from ..db.cache import CacheManager
from ..db.connection import open_connection
from ..utils.common import compute_file_hash
from ..utils.dreamsim import compute_dreamsim_distance_matrix
from ..utils.feature import PathsWithHashes, get_image_features_use_cache
from ..utils.image import IMG_EXTS
from ..utils.progress import ProgressFactory, tqdm_factory
from ..utils.result import Result


def umap_order(
    D: NDArray[np.float32],
    n_neighbors: int = 10,
    min_dist: float = 0.0,
) -> list[int]:
    warnings.filterwarnings(
        "ignore",
        message="using precomputed metric; inverse_transform will be unavailable",
    )
    warnings.filterwarnings(
        "ignore",
        message="n_jobs value .* overridden .* random_state",
    )

    reducer = umap.UMAP(
        n_components=1,
        metric="precomputed",
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        random_state=42,  # 固定种子会禁用并行
    )
    embedding = cast("np.ndarray", reducer.fit_transform(D)).reshape(-1)
    order = np.argsort(embedding)
    return order.tolist()


def get_sort_units(root: Path) -> list[Path]:
    """
    递归获取所有排序单元目录。
    排序单元定义：目录下有图片（直接所属，不嵌套子目录的图片）

    Args:
        root: 根目录

    Returns:
        sort_units: 目录列表，每个目录包含至少一张图片
    """
    sort_units: list[Path] = []

    for path in root.rglob("*"):
        if not path.is_dir():
            continue
        # 检查该目录下是否有文件（不递归子目录）
        has_image = any(f.is_file() for f in path.iterdir())
        no_sort = (path / ".nosort").exists()

        if has_image and not no_sort:
            sort_units.append(path)

    if any(f.is_file() for f in root.iterdir()):
        sort_units.append(root)

    return sort_units


def has_uniform_prefix(files: list[Path]) -> bool:
    """
    判断文件列表是否都具有相同前缀
    前缀需要与父目录的名字相同
    """
    if not files:
        return True  # 空列表视为统一

    parent_name = files[0].parent.name
    return all(f.stem.startswith(parent_name) for f in files)


def sort_images_by_perceptual_similarity(
    images_root: Path,
    avoid_sorted: bool,
    *,
    make_progress: ProgressFactory | None = None,
) -> Result[None]:
    """
    根据 DreamSim 感知相似度对图片进行排序，使得相似图片相邻

    Args:
        images_root: 图片文件夹路径
        avoid_sorted: 避免对已排序目录进行排序
    Notes:
        - 递归遍历所有子目录
        - 排序单元是每个目录，不递归
        - 如果存在 .nosort 文件，该目录将被忽略
    """
    with closing(open_connection()) as conn:
        cache = CacheManager(conn)
        factory = make_progress or tqdm_factory
        sort_units = get_sort_units(images_root)
        exts = IMG_EXTS
        outer = factory(len(sort_units), "排序图片")
        for unit in sort_units:
            image_paths: list[Path] = []
            for ext in exts:
                image_paths.extend(unit.glob(ext))
            image_paths.sort()  # 尽量让输入序列稳定

            if len(image_paths) <= 2:
                outer.update(1)
                continue

            if has_uniform_prefix(image_paths) and avoid_sorted:
                outer.update(1)
                continue

            outer.set_postfix(unit.name)

            image_hashes = [compute_file_hash(path) for path in image_paths]
            features, _ = get_image_features_use_cache(
                "dreamsim",
                paths_and_hashes=PathsWithHashes(image_paths, image_hashes),
                cache=cache,
                make_progress=factory,
            )
            embeddings = np.stack(features, axis=0)
            distances = compute_dreamsim_distance_matrix(embeddings)

            n_neighbors = min(10, max(2, len(image_paths) // 2)) if len(image_paths) < 200 else 20
            order = umap_order(distances, n_neighbors=n_neighbors)

            # 根据 order 重命名图片（为了避免多次排序重名导致报错，先改为临时名称）
            temp_paths: list[Path] = []
            for idx in order:
                old_path = image_paths[idx]
                temp_path = old_path.with_name(f"__temp_{old_path.name}")
                old_path.rename(temp_path)
                temp_paths.append(temp_path)

            for rank, _ in enumerate(order):
                old_path = temp_paths[rank]
                new_path = old_path.with_name(f"{unit.name}_{rank:04d}{old_path.suffix}")
                old_path.rename(new_path)

            outer.update(1)
        outer.close()
        return Result(True, "排序完成")
