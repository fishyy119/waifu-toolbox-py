import hashlib
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


def compute_file_hash(path: Path, algo: str = "sha1") -> bytes:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.digest()


def farthest_point_sampling(
    dist_mat: NDArray[np.float32],
    k: int,
    start: int | None = None,
) -> list[int]:
    """
    最远点采样（Farthest Point Sampling, FPS）

    Args:
        dist_mat (NDArray[np.float32]): 距离矩阵，形状为 (N, N)，dist_mat[i, j] 表示 i 与 j 的距离
        k (int): 目标采样点数量
        start (int | None): 起始点索引，为 None 时自动选择全局最远点

    Returns:
        List[int]: 采样得到的索引列表，长度为 min(k, N)
    """
    assert dist_mat.ndim == 2
    assert dist_mat.shape[0] == dist_mat.shape[1]

    N = dist_mat.shape[0]
    if k >= N:
        return list(range(N))

    # 选择起始点
    if start is None:
        # 选择平均距离最大的点，避免随机性
        start = int(np.argmax(dist_mat.mean(axis=1)))

    selected = np.empty(k, dtype=np.int64)
    selected[0] = start

    # min_dist[i] = 当前已选集合到 i 的最小距离
    min_dist = dist_mat[start].copy()

    for i in range(1, k):
        idx = np.argmax(min_dist)
        selected[i] = idx

        # 更新每个点到已选集合的最小距离
        min_dist = np.minimum(min_dist, dist_mat[idx])

    return selected.tolist()
