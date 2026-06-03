# pyright: standard

import pickle
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

import numpy as np
from numpy.typing import NDArray
from tqdm import tqdm

from ..utils.common import compute_file_hash, farthest_point_sampling
from ..utils.console import log_info
from ..utils.feature import get_image_features_use_cache
from ..utils.image import IMG_EXTS

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
                from imgutils.metrics import ccip_batch_differences

                distance_matrix = ccip_batch_differences([self.features[i, :] for i in indices])
                sample_indices_local = farthest_point_sampling(distance_matrix, max_num)
                sample_indices = [indices[i] for i in sample_indices_local]

                selected_indices.extend(sample_indices)

        # 同步裁剪所有成员变量
        self.features = self.features[selected_indices, :]
        self.labels = [self.labels[i] for i in selected_indices]
        self.hashes = [self.hashes[i] for i in selected_indices]
        self._is_partial = True

    @staticmethod
    def scan_imgs_with_label(repo_path: Path) -> Tuple[List[Path], List[str]]:
        exts = IMG_EXTS
        image_paths: List[Path] = []
        labels: List[str] = []

        for category_dir in repo_path.iterdir():
            if not category_dir.is_dir():
                continue

            label = category_dir.name
            for ext in exts:
                for img_path in category_dir.rglob(ext):
                    image_paths.append(img_path)
                    labels.append(label)

        return image_paths, labels

    def purge(self, name: str) -> bool:
        """移除索引中已经不存在于磁盘的图片记录"""
        self.load(name)
        assert self.repo_path is not None
        assert self.features is not None

        image_paths, _ = self.scan_imgs_with_label(self.repo_path)
        existing_hashes: Set[bytes] = set()

        for p in tqdm(image_paths, desc="计算现有文件哈希"):
            h = compute_file_hash(p)
            existing_hashes.add(h)

        # 要考虑数据库内部记录的hashes有重复的情况
        seen: Set[bytes] = set()
        keep_indices: List[int] = []

        for i, h in enumerate(self.hashes):
            if h not in existing_hashes:
                continue  # 磁盘不存在
            if h in seen:
                continue  # 索引内部重复
            seen.add(h)
            keep_indices.append(i)

        if len(keep_indices) == len(self.hashes):
            log_info("No images to purge.")
            return False

        # 同步移除 labels / features / hashes
        removed = len(self.hashes) - len(keep_indices)
        self.labels = [self.labels[i] for i in keep_indices]
        self.features = self.features[keep_indices]
        self.hashes = [self.hashes[i] for i in keep_indices]

        log_info(f"Purged {removed} images from repository '{name}'.")
        return True

    def update(self, name: str) -> bool:
        """更新仓库索引（仓库根路径已经被记录在其中）"""
        self.load(name)
        assert self.repo_path is not None
        assert self.features is not None

        image_paths, labels = self.scan_imgs_with_label(self.repo_path)

        hash_to_index: Dict[bytes, int] = {h: i for i, h in enumerate(self.hashes)}
        updated_labels = 0
        new_hashes: List[bytes] = []
        new_paths: List[Path] = []
        new_labels: List[str] = []

        for p, label in tqdm(zip(image_paths, labels), total=len(image_paths), desc="扫描并同步索引"):
            h = compute_file_hash(p)

            if h in hash_to_index:  # 已存在索引中
                idx = hash_to_index[h]
                if self.labels[idx] != label:  # 分类发生变化，仅更新 label
                    self.labels[idx] = label
                    updated_labels += 1
            else:  # 新图片
                new_hashes.append(h)
                new_paths.append(p)
                new_labels.append(label)

        if not new_paths:
            log_info(f"无新增图片，更新了 {updated_labels} 个标签。")
            if updated_labels == 0:
                return False
            return True

        new_features, _ = get_image_features_use_cache("ccip", paths_and_hashes=(new_paths, new_hashes))

        # 更新索引
        self.features = np.concatenate([self.features, np.stack(new_features, axis=0)], axis=0)

        self.hashes.extend(new_hashes)
        self.labels.extend(new_labels)

        log_info(f"增加了 {len(new_paths)} 张新图片，更新了 {updated_labels} 个标签。")

        return True

    def deduplicate(self, name: str) -> bool:
        """基于文件hash去重仓库中的重复图片，如果标签与记录不符输出提示手动处理"""
        self.load(name)
        assert self.repo_path is not None
        assert self.features is not None

        image_paths, labels = self.scan_imgs_with_label(self.repo_path)

        @dataclass
        class HashIndexInfo:
            label: str
            hit: int = 0

        hash_index: Dict[bytes, HashIndexInfo] = {
            h: HashIndexInfo(label=self.labels[i]) for i, h in enumerate(self.hashes)
        }

        for p, label in tqdm(zip(image_paths, labels), total=len(image_paths), desc="扫描并同步索引"):
            h = compute_file_hash(p)

            if h in hash_index:  # 已存在索引中
                index_info = hash_index[h]

                if index_info.label != label:
                    log_info(
                        f"发现与数据库存储标签不符的图片[green]",
                        f"{index_info.label}[/green]!=[red]{label}[/red]",
                        f"：[orchid]{p}[/orchid]",
                        sep="",
                    )
                    continue

                index_info.hit += 1

                if index_info.hit > 1:
                    p.unlink()
                    log_info(f"删除重复图片: [orchid]{p}[/orchid]")

        return True

    def scan_init(self, repo_name: str, path: Path) -> bool:
        """初始化扫描一个已分类仓库"""
        image_paths, labels = self.scan_imgs_with_label(path)

        # 计算 hash
        hashes: List[bytes] = []
        valid_paths: List[Path] = []
        valid_labels: List[str] = []

        for p, label in tqdm(zip(image_paths, labels), total=len(image_paths), desc="计算文件哈希"):
            h = compute_file_hash(p)
            if h in self.hashes:
                continue
            hashes.append(h)
            valid_paths.append(p)
            valid_labels.append(label)

        if not valid_paths:
            return False

        features, _ = get_image_features_use_cache("ccip", paths_and_hashes=(valid_paths, hashes))

        # 写入索引
        self.features = np.stack(features, axis=0)

        self.repo_name = repo_name
        self.repo_path = path
        self.hashes = hashes
        self.labels = valid_labels

        return True
