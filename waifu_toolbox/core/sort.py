import shutil
import warnings
from pathlib import Path
from typing import List, Tuple, cast

import numpy as np
import umap
from imgutils.metrics import lpips_difference, lpips_extract_feature
from numpy.typing import NDArray
from scipy.sparse.csgraph import minimum_spanning_tree
from tqdm import tqdm

from ..db.cache import CACHE_ROOT
from ..utils.image import IMG_EXTS, load_image

CACHE_DIR = CACHE_ROOT / "lpips"


def mst_tsp_order(D: NDArray[np.float32]) -> List[int]:
    """
    使用 MST 近似 TSP 得到图片排序
    （这种方法没有考虑优先簇内）

    Args:
        D: N x N 感知距离矩阵

    Returns:
        order: 图片索引的一维序列，使相似图片相邻
    """
    assert D.ndim == 2 and D.shape[0] == D.shape[1], "距离矩阵必须是方阵"
    N = D.shape[0]

    # 1. 构建最小生成树
    mst_sparse = minimum_spanning_tree(D)
    mst = mst_sparse.toarray()

    # 2. 将 MST 转为邻接列表
    eps = 1e-9
    adj = {i: [] for i in range(N)}
    for i in range(N):
        for j in range(N):
            if mst[i, j] > eps or mst[j, i] > eps:
                adj[i].append(j)
                adj[j].append(i)

    # 3. DFS 遍历 MST 得到路径
    visited = [False] * N
    order = []

    def dfs(u: int):
        visited[u] = True
        order.append(u)
        for v in adj[u]:
            if not visited[v]:
                dfs(v)

    degree = [len(adj[i]) for i in range(N)]
    best_start = int(np.argmax(degree))
    dfs(best_start)  # 从最佳起始点开始遍历
    return order


def umap_order(
    D: NDArray[np.float32],
    n_neighbors: int = 10,
    min_dist: float = 0.0,
) -> List[int]:
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
    embedding = cast(np.ndarray, reducer.fit_transform(D)).reshape(-1)
    order = np.argsort(embedding)
    return order.tolist()


def save_lpips_chunk(chunk_idx: int, features: List) -> None:
    path = CACHE_DIR / f"chunk_{chunk_idx:05d}.npz"
    arr = np.empty(len(features), dtype=object)
    arr[:] = features  # 整体赋值，不拆 tuple

    np.savez_compressed(path, features=arr)


def load_lpips_chunk(chunk_idx: int) -> List[Tuple[np.ndarray, ...]]:
    path = CACHE_DIR / f"chunk_{chunk_idx:05d}.npz"
    data = np.load(path, allow_pickle=True)
    return list(data["features"])


def compute_lpips_distance_matrix(images: List) -> NDArray[np.float32]:
    """
    计算图片的 LPIPS 感知距离矩阵

    Args:
        images: 图片数组

    Returns:
        D: N x N 感知距离矩阵
    """
    N = len(images)
    D = np.zeros((N, N), dtype=np.float32)

    total = N * (N + 1) // 2
    with tqdm(total=total, desc="计算 LPIPS 距离", leave=False) as pbar:
        for i in range(N):
            for j in range(i, N):
                diff = lpips_difference(images[i], images[j])
                D[i, j] = D[j, i] = diff

            pbar.update(N - i)

    return D


def compute_lpips_distance_matrix_cache() -> NDArray[np.float32]:
    """
    计算图片的 LPIPS 感知距离矩阵（使用缓存版本）

    Args:
        images: 图片数组

    Returns:
        D: N x N 感知距离矩阵
    """
    # ============================
    # 1. 枚举 chunk
    # ============================
    chunk_paths = sorted(CACHE_DIR.glob("chunk_*.npz"))
    if not chunk_paths:
        raise RuntimeError("未找到 LPIPS 特征缓存 chunk")

    num_chunks = len(chunk_paths)

    # ============================
    # 2. 统计每个 chunk 的大小 & 全局偏移
    # ============================
    chunk_sizes: List[int] = []
    for path in chunk_paths:
        data = np.load(path, allow_pickle=True)
        chunk_sizes.append(len(data["features"]))

    chunk_offsets: List[int] = []
    offset = 0
    for size in chunk_sizes:
        chunk_offsets.append(offset)
        offset += size

    N = offset  # 图片总数
    if N == 0:
        raise RuntimeError("LPIPS 特征缓存为空")

    # ============================
    # 3. 准备距离矩阵 & tqdm
    # ============================
    total_pairs = N * (N + 1) // 2
    D = np.zeros((N, N), dtype=np.float32)

    # ============================
    # 4. chunk × chunk 计算
    # ============================
    with tqdm(total=total_pairs, desc="计算 LPIPS 距离", leave=False) as pbar:
        for ci in range(num_chunks):
            feats_i = load_lpips_chunk(ci)
            offset_i = chunk_offsets[ci]
            size_i = len(feats_i)

            for cj in range(ci, num_chunks):
                feats_j = load_lpips_chunk(cj)
                offset_j = chunk_offsets[cj]
                size_j = len(feats_j)

                if ci == cj:
                    # TODO: 这里是不是内存占用无端翻倍了？
                    # chunk 内：只算上三角
                    for i in range(size_i):
                        gi = offset_i + i
                        fi = feats_i[i]
                        for j in range(i, size_i):
                            gj = offset_j + j
                            diff = lpips_difference(fi, feats_j[j])
                            D[gi, gj] = D[gj, gi] = diff
                        pbar.update(size_i - i)
                else:
                    # chunk 间：全矩阵
                    for i in range(size_i):
                        gi = offset_i + i
                        fi = feats_i[i]
                        for j in range(size_j):
                            gj = offset_j + j
                            diff = lpips_difference(fi, feats_j[j])
                            D[gi, gj] = D[gj, gi] = diff
                        pbar.update(size_j)

                # 立即释放
                del feats_j

            del feats_i

    return D


def get_sort_units(root: Path) -> List[Path]:
    """
    递归获取所有排序单元目录。
    排序单元定义：目录下有图片（直接所属，不嵌套子目录的图片）

    Args:
        root: 根目录

    Returns:
        sort_units: 目录列表，每个目录包含至少一张图片
    """
    sort_units: List[Path] = []

    for path in root.rglob("*"):
        if not path.is_dir():
            continue
        # 检查该目录下是否有文件（不递归子目录）
        has_image = any(f.is_file() for f in path.iterdir())
        if has_image:
            sort_units.append(path)

    if any(f.is_file() for f in root.iterdir()):
        sort_units.append(root)

    return sort_units


def has_uniform_prefix(files: List[Path]) -> bool:
    """
    判断文件列表是否都具有相同前缀
    前缀需要与父目录的名字相同
    """
    if not files:
        return True  # 空列表视为统一

    parent_name = files[0].parent.name
    return all(f.stem.startswith(parent_name) for f in files)


def sort_images_by_perceptual_similarity(images_root: Path, memory_limit: int, avoid_sorted: bool) -> None:
    """
    根据感知相似度对图片进行排序，使得相似图片相邻

    Args:
        images_root: 图片文件夹路径
        memory_limit: 内存限制（MB）
        avoid_sorted: 避免对已排序目录进行排序

    Returns:
        order: 图片索引的一维序列，使相似图片相邻

    Notes:
        - 递归遍历所有子目录
        - 排序单元是每个目录，不递归
    """
    sort_units = get_sort_units(images_root)
    exts = IMG_EXTS
    for unit in (pbar_root := tqdm(sort_units, desc="排序图片", unit="folder")):
        image_paths: List[Path] = []
        for ext in exts:
            image_paths.extend(list(unit.glob(ext)))

        if len(image_paths) <= 2:
            continue

        if has_uniform_prefix(image_paths) and avoid_sorted:
            # 已排序目录，跳过
            continue

        pbar_root.set_postfix_str(unit.name)

        chunk_size = int((memory_limit / 1024) * 50)
        use_cache = chunk_size * 2 <= len(image_paths)
        chunk_idx = 0
        buf_features = []

        if use_cache:
            if CACHE_DIR.exists():
                shutil.rmtree(CACHE_DIR)
            CACHE_DIR.mkdir(exist_ok=True, parents=True)

            with tqdm(total=len(image_paths), desc="提取 LPIPS 特征", unit="img", leave=False) as pbar:
                for chunk_start in range(0, len(image_paths), chunk_size):
                    for p in image_paths[chunk_start : chunk_start + chunk_size]:
                        image = load_image(p)
                        feature = lpips_extract_feature(image)
                        buf_features.append(feature)
                        pbar.update(1)

                    save_lpips_chunk(chunk_idx, buf_features)
                    buf_features.clear()
                    chunk_idx += 1

            D = compute_lpips_distance_matrix_cache()
        else:
            with tqdm(total=len(image_paths), desc="提取 LPIPS 特征", unit="img", leave=False) as pbar:
                for p in image_paths:
                    image = load_image(p)
                    feature = lpips_extract_feature(image)
                    buf_features.append(feature)
                    pbar.update(1)

            D = compute_lpips_distance_matrix(buf_features)

        # order = mst_tsp_order(D)
        if len(image_paths) < 200:
            n_neighbors = min(10, max(2, len(image_paths) // 2))
        else:
            n_neighbors = 20
        order = umap_order(D, n_neighbors=n_neighbors)

        # 根据 order 重命名图片（为了避免多次排序重名导致报错，先改为临时名称）
        temp_paths: List[Path] = []
        for idx in order:
            old_path = image_paths[idx]
            temp_path = old_path.with_name(f"__temp_{old_path.name}")
            old_path.rename(temp_path)
            temp_paths.append(temp_path)

        for rank, idx in enumerate(order):
            old_path = temp_paths[rank]
            new_path = old_path.with_name(f"{unit.name}_{rank:04d}{old_path.suffix}")
            old_path.rename(new_path)

    return
