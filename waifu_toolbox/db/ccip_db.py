import pickle
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from numpy.typing import NDArray
from tqdm import tqdm

from ..utils.common import compute_file_hash
from ..utils.console import log_info
from ..utils.image import load_image

DB_ROOT = Path(__file__).parents[2] / "database/ccip"
DB_ROOT.mkdir(exist_ok=True)


class ImageDBCCIP:
    def __init__(self, repo_name: str | None = None):
        self.features: NDArray[np.float32] | None = None
        self.hashes: List[bytes] = []
        self.labels: List[str] = []
        self._is_partial: bool = False  # 如果进行了部分采样操作，则应当在保存时拒绝

        self._repo_name: str | None = None
        self.db_path: Path | None = None
        self.repo_path: Path | None = None

        if repo_name is not None:
            self.load(repo_name)

    @property
    def size(self) -> int:
        return len(self.hashes)

    @property
    def repo_name(self) -> str | None:
        return self._repo_name

    @repo_name.setter
    def repo_name(self, name: str):
        self._repo_name = name
        self.db_path = DB_ROOT / name

    def load(self, repo_name: str):
        self.repo_name = repo_name
        assert self.db_path is not None
        feat_file = self.db_path / "index.npz"
        meta_file = self.db_path / "meta.pkl"

        if feat_file.exists():
            self.features = np.load(feat_file)["features"]
        else:
            self.features = None

        if meta_file.exists():
            with open(meta_file, "rb") as f:
                meta = pickle.load(f)
            self.hashes = meta["hashes"]
            self.labels = meta["labels"]
            self.repo_path = Path(meta["repo_path"])

        self._is_partial = False

    def save(self):
        assert self.db_path is not None, "db_path 未设置，无法保存"
        assert self.repo_path is not None, "repo_path 未设置，无法保存"
        assert not self._is_partial, "当前数据库为部分采样状态，拒绝保存以防数据丢失"

        db_path = self.db_path
        db_path.mkdir(exist_ok=True)

        if self.features is not None:
            np.savez_compressed(
                db_path / "index.npz",
                features=self.features,
            )

        with open(db_path / "meta.pkl", "wb") as f:
            pickle.dump(
                {
                    "hashes": self.hashes,
                    "labels": self.labels,
                    "repo_path": str(self.repo_path),
                },
                f,
                protocol=pickle.HIGHEST_PROTOCOL,
            )

    # TODO: 基于距离采样
    def sample(self, max_num: int) -> None:
        """
        从每个类别中随机采样最多 max_num 个样本，用于分类参考。
        会就地覆盖 features / hashes / labels。
        """
        assert self.features is not None
        assert len(self.features) == len(self.labels) == len(self.hashes)

        # 按 label 分组索引
        label_to_indices: Dict[str, List[int]] = defaultdict(list)
        for idx, label in enumerate(self.labels):
            label_to_indices[label].append(idx)

        # 每个类别随机采样
        selected_indices: List[int] = []
        for label, indices in label_to_indices.items():
            if len(indices) <= max_num:
                selected_indices.extend(indices)
            else:
                selected_indices.extend(random.sample(indices, max_num))

        # 同步裁剪所有成员变量
        self.features = self.features[selected_indices, :]
        self.labels = [self.labels[i] for i in selected_indices]
        self.hashes = [self.hashes[i] for i in selected_indices]
        self._is_partial = True

    @staticmethod
    def scan_imgs_with_label(repo_path: Path) -> Tuple[List[Path], List[str]]:
        exts = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif")
        image_paths: list[Path] = []
        labels: list[str] = []

        for category_dir in repo_path.iterdir():
            if not category_dir.is_dir():
                continue

            label = category_dir.name
            for ext in exts:
                for img_path in category_dir.rglob(ext):
                    image_paths.append(img_path)
                    labels.append(label)

        return image_paths, labels

    @staticmethod
    def extract_features(imgs) -> NDArray[np.float32]:
        from imgutils.metrics.ccip import ccip_extract_feature

        features_list: List[NDArray[np.float32]] = []
        for img in tqdm(imgs, desc="提取特征"):
            # 虽然有另一个batch函数，但不知道他是怎么搞的，一直在分配内存时报错。。。
            feature = ccip_extract_feature(img)  # pyright: ignore[reportArgumentType]
            features_list.append(feature)
            # shape: (D,)

        features = np.stack(features_list, axis=0)  # shape: (N, D)
        return features

    def purge(self, name: str) -> bool:
        """移除索引中已经不存在于磁盘的图片记录"""
        self.load(name)
        assert self.repo_path is not None
        assert self.features is not None

        image_paths, _ = self.scan_imgs_with_label(self.repo_path)
        existing_hashes = set()

        for p in tqdm(image_paths, desc="计算现有文件哈希"):
            h = compute_file_hash(p)
            existing_hashes.add(h)

        # 找出 self.hashes 中不再存在的索引
        remove_indices = [i for i, h in enumerate(self.hashes) if h not in existing_hashes]
        if not remove_indices:
            log_info("No images to purge.")
            return False

        # 同步移除 labels / features / hashes
        self.labels = [v for i, v in enumerate(self.labels) if i not in remove_indices]
        self.features = np.delete(self.features, remove_indices, axis=0)
        self.hashes = [h for i, h in enumerate(self.hashes) if i not in remove_indices]

        log_info(f"Purged {len(remove_indices)} images from repository '{name}'.")
        return True

    def update(self, name: str) -> bool:
        """更新仓库索引（仓库根路径已经被记录在其中）"""
        self.load(name)
        assert self.repo_path is not None
        assert self.features is not None

        image_paths, labels = self.scan_imgs_with_label(self.repo_path)

        # TODO: 未考虑移动已有图片分类的情况
        # 计算文件 hash 并去重
        new_hashes: list[bytes] = []
        new_paths: list[Path] = []
        new_labels: list[str] = []

        for p, label in tqdm(zip(image_paths, labels), total=len(image_paths), desc="计算文件哈希"):
            h = compute_file_hash(p)
            if h in self.hashes:  # 已存在索引中
                continue
            new_hashes.append(h)
            new_paths.append(p)
            new_labels.append(label)

        if not new_paths:
            log_info("No new images to add.")
            return False

        # 提取特征
        images = [load_image(p) for p in tqdm(new_paths, desc="加载图片")]
        new_features = self.extract_features(images)

        # 更新索引
        self.features = np.concatenate([self.features, new_features], axis=0)

        self.hashes.extend(new_hashes)
        self.labels.extend(new_labels)

        return True

    def scan_init(self, repo_name: str, path: Path) -> bool:
        """初始化扫描一个已分类仓库"""
        image_paths, labels = self.scan_imgs_with_label(path)

        # 计算 hash
        hashes: list[bytes] = []
        valid_paths: list[Path] = []
        valid_labels: list[str] = []

        for p, label in tqdm(zip(image_paths, labels), total=len(image_paths), desc="计算文件哈希"):
            h = compute_file_hash(p)
            if h in self.hashes:
                continue
            hashes.append(h)
            valid_paths.append(p)
            valid_labels.append(label)

        if not valid_paths:
            return False

        images = [load_image(p) for p in tqdm(valid_paths, desc="加载图片")]

        # 写入索引
        self.features = self.extract_features(images)

        self.repo_name = repo_name
        self.repo_path = path
        self.hashes = hashes
        self.labels = valid_labels

        return True
