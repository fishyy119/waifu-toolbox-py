import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from imgutils.metrics.ccip import ccip_clustering
from numpy.typing import NDArray

from ..db.ccip_db import ImageDBCCIP
from ..utils.console import log_error, log_info
from ..utils.feature import get_image_features_use_cache


def _extract_features_to_list(features: NDArray | List[NDArray], indices: List[int] | None = None) -> List[NDArray]:
    """将 (N,D) 的特征向量集合（或特征向量列表）按索引提取为 List[(D,)]"""
    if isinstance(features, list):
        return [features[i] for i in indices] if indices is not None else features
    else:
        indices = indices if indices is not None else list(range(features.shape[0]))
        return [features[i] for i in indices]


def classify_by_ccip(labeled_repo: str, to_classify_root: Path, num_references: int) -> None:
    """
    Args:
        labeled_repo (str): 目标仓库名（预生成的数据库）.
        to_classify_root (Path): 待分类图片根目录.
        num_references (int): 每个类别使用的参考图像数量最大值.

    Notes:
        - 函数会生成报告文件夹，路径格式为 `{labeled_repo}.report.YYYYMMDD_HHMMSS`，
          每个类别一个子文件夹，子文件夹内按聚类 ID 进一步分类。
        - `__unknown__` 为保留名，表示无匹配。
    """
    # -----------------------------
    # 1. 加载已标注图片
    # -----------------------------
    db = ImageDBCCIP(labeled_repo)
    db.sample(num_references)

    labeled_categories = db.labels
    labeled_features = db.features
    labeled_hashes = db.hashes
    assert labeled_features is not None
    assert len(labeled_categories) == labeled_features.shape[0] == len(labeled_hashes)

    # -----------------------------
    # 2. 加载待分类图片
    # -----------------------------
    to_classify_features, to_classify_paths = get_image_features_use_cache("ccip", img_folder_root=to_classify_root)
    if not to_classify_paths:
        raise RuntimeError("未找到待分类图片")

    # -----------------------------
    # 3. 合并图片
    # -----------------------------
    all_features = _extract_features_to_list(labeled_features) + to_classify_features
    major_keys = labeled_hashes + to_classify_paths  # 这就相当于主键了
    label_dict = {p: c for p, c in zip(labeled_hashes, labeled_categories)}

    # -----------------------------
    # 4. 特征聚类
    # -----------------------------
    mapping: List[int] = ccip_clustering(all_features)  # pyright: ignore
    # ? AttributeError: 'list' object has no attribute 'tolist'
    # 库的类型注解标错了。。。。

    # -----------------------------
    # INDEX: 按聚类簇创建索引
    # -----------------------------
    @dataclass
    class ClusterInfo:
        known_labels: List[str] = field(default_factory=list)
        to_classify_indices: List[int] = field(default_factory=list)
        label: str = "__unknown__"

    cluster_index: Dict[int, ClusterInfo] = defaultdict(ClusterInfo)

    assert len(major_keys) == len(mapping)
    hashes_len = len(labeled_hashes)
    for ind, (mkey, cluster_id) in enumerate(zip(major_keys, mapping)):
        if isinstance(mkey, bytes):  # 这种类型就代表已经在数据库中有标注了
            cluster_index[cluster_id].known_labels.append(label_dict[mkey])
        else:  # 待分类图片，减去已标注图片数，得到待分类图片索引
            cluster_index[cluster_id].to_classify_indices.append(ind - hashes_len)

    for cluster_id, cluster_info in cluster_index.items():
        known_labels = cluster_info.known_labels
        if known_labels and cluster_id != -1:
            vote = Counter(known_labels).most_common(1)[0][0]
            cluster_index[cluster_id].label = vote

    # -----------------------------
    # INDEX: 按投票分类创建索引
    # -----------------------------
    category_index: Dict[str, List[int]] = defaultdict(list)
    for _, cluster_info in cluster_index.items():
        category_index[cluster_info.label].extend(cluster_info.to_classify_indices)

    # -----------------------------
    # 分配类别给待分类图片并保存
    # -----------------------------
    report_dir_name = f"{labeled_repo}.report.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    report_root = to_classify_root.parent / report_dir_name
    report_root.mkdir(exist_ok=True)

    # 每个分类的候选额外进行一次聚类，提升报告质量
    for category, indices in category_index.items():
        if len(indices) < 5:  #  这是聚类方法需要的最小样本数量，过小应跳过
            continue
        candidate_features = _extract_features_to_list(to_classify_features, indices)
        candidate_mapping: List[int] = ccip_clustering(candidate_features)  # type: ignore

        for p_ind, c_id2 in zip(indices, candidate_mapping):
            path = to_classify_paths[p_ind]
            cluster_dir = report_root / category / f"{c_id2}"
            cluster_dir.mkdir(parents=True, exist_ok=True)

            target_file = cluster_dir / path.name
            if target_file.exists():
                log_error(f"发现重复的文件名: [orchid]{target_file.name}[/orchid]，请先手动处理")
                exit(1)
            shutil.copy2(path, target_file)

    log_info(f"report 保存路径: [orchid]{report_root}[/orchid]")


def just_cluster_by_ccip(to_cluster_root: Path, inplace: bool = False) -> Tuple[List[Path], List[int]]:
    """
    仅聚类，不参考仓库分类
    """
    to_cluster_features, to_cluster_paths = get_image_features_use_cache("ccip", img_folder_root=to_cluster_root)
    if not to_cluster_paths:
        raise RuntimeError("未找到待分类图片")

    mapping: List[int] = ccip_clustering(to_cluster_features)  # pyright: ignore
    # ? AttributeError: 'list' object has no attribute 'tolist'
    # 库的类型注解标错了。。。。

    # -----------------------------
    # 保存
    # -----------------------------
    if inplace:
        report_root = to_cluster_root
        file_op = shutil.move
    else:
        report_dir_name = f"{to_cluster_root.name}.report.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        report_root = to_cluster_root.parent / report_dir_name
        report_root.mkdir(exist_ok=True)
        file_op = shutil.copy2

    for path, cluster_id in zip(to_cluster_paths, mapping):
        cluster_dir = report_root / f"{cluster_id}"
        cluster_dir.mkdir(parents=True, exist_ok=True)

        target_file = cluster_dir / path.name
        if target_file.exists():
            log_error(f"发现重复的文件名: [orchid]{target_file.name}[/orchid]，请先手动处理")
            exit(1)
        file_op(path, target_file)

    log_info(f"report 保存路径: [orchid]{report_root}[/orchid]")

    return to_cluster_paths, mapping
