# pyright: standard

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import numpy as np

from ..db.cache import CacheName
from ..db.repo import ImageEntry, ImageUpdate, RepoStorage
from ..utils.common import compute_file_hash, farthest_point_sampling
from ..utils.image import IMG_EXTS
from ..utils.progress import ProgressFactory, tqdm_factory
from .feature import PathsWithHashes, get_image_features_use_cache


class ScanResult(NamedTuple):
    paths: list[Path]
    labels: list[str]


class _SeenImage(NamedTuple):
    path: Path
    label: str


class ImageRepo(RepoStorage):
    """在仓库持久化能力上实现扫描、特征计算和文件整理流程。"""

    def sample(self, max_num: int) -> None:
        """
        从每个类别中随机采样最多 max_num 个样本，用于分类参考。
        会就地覆盖 features / hashes / labels。
        """
        assert self.ccip_features is not None
        assert len(self.ccip_features) == len(self.labels) == len(self.hashes)

        label_to_indices: dict[str, list[int]] = defaultdict(list)
        for idx, label in enumerate(self.labels):
            label_to_indices[label].append(idx)

        selected_indices: list[int] = []
        for _label, indices in label_to_indices.items():
            if len(indices) <= max_num:
                selected_indices.extend(indices)
            else:
                from imgutils.metrics import ccip_batch_differences

                distance_matrix = ccip_batch_differences([self.ccip_features[i, :] for i in indices])
                sample_indices_local = farthest_point_sampling(distance_matrix, max_num)
                sample_indices = [indices[i] for i in sample_indices_local]

                selected_indices.extend(sample_indices)

        self.ccip_features = self.ccip_features[selected_indices, :]
        if self.dreamsim_features is not None:
            self.dreamsim_features = self.dreamsim_features[selected_indices, :]
        self.labels = [self.labels[i] for i in selected_indices]
        self.hashes = [self.hashes[i] for i in selected_indices]
        self.relative_paths = [self.relative_paths[i] for i in selected_indices]

    @staticmethod
    def scan_imgs_with_label(repo_path: Path) -> ScanResult:
        exts = IMG_EXTS
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

        return ScanResult(image_paths, labels)

    def purge(self, name: str, *, make_progress: ProgressFactory | None = None) -> int:
        """移除索引中已经不存在于磁盘的图片记录，返回删除数量"""
        self.load(name)
        assert self.repo_path is not None
        assert self._repo_id is not None

        image_paths, _ = self.scan_imgs_with_label(self.repo_path)
        existing_hashes: set[bytes] = set()

        factory = make_progress or tqdm_factory
        bar = factory(len(image_paths), "计算现有文件哈希")
        for p in image_paths:
            h = compute_file_hash(p)
            existing_hashes.add(h)
            bar.update(1)
        bar.close()

        return self.purge_except(existing_hashes)

    @dataclass
    class UpdateResult:
        new_images: int
        updated_labels: int

    def update(
        self,
        name: str,
        extract_ccip: bool = False,
        extract_dreamsim: bool = False,
        *,
        make_progress: ProgressFactory | None = None,
    ) -> "ImageRepo.UpdateResult":
        """更新仓库索引，按需提取特征"""
        self.load(name)
        assert self.repo_path is not None
        assert self._repo_id is not None

        image_paths, labels = self.scan_imgs_with_label(self.repo_path)

        hash_to_index: dict[bytes, int] = {h: i for i, h in enumerate(self.hashes)}
        hash_to_path: dict[bytes, Path] = {}
        updated_labels = 0
        new_entries: list[ImageEntry] = []
        existing_updates: list[ImageUpdate] = []

        factory = make_progress or tqdm_factory
        bar = factory(len(image_paths), "扫描并同步索引")
        for p, label in zip(image_paths, labels, strict=False):
            h = compute_file_hash(p)
            hash_to_path[h] = p
            rel = str(p.relative_to(self.repo_path))

            if h in hash_to_index:
                idx = hash_to_index[h]
                if self.labels[idx] != label:
                    updated_labels += 1
                existing_updates.append(ImageUpdate(label, rel, h))
            else:
                new_entries.append(ImageEntry(h, label, rel))
            bar.update(1)
        bar.close()

        self.sync_entries(new_entries, existing_updates)

        if extract_ccip:
            self._extract_missing_feature("ccip", hash_to_path, make_progress=make_progress)
        if extract_dreamsim:
            self._extract_missing_feature("dreamsim", hash_to_path, make_progress=make_progress)

        return self.UpdateResult(new_images=len(new_entries), updated_labels=updated_labels)

    @dataclass
    class DeduplicateResult:
        deleted: int
        label_mismatches: list[str]

    def deduplicate(self, name: str, *, make_progress: ProgressFactory | None = None) -> "ImageRepo.DeduplicateResult":
        """基于文件hash去重仓库中的重复图片，返回去重结果"""
        self.load(name)
        assert self.repo_path is not None

        image_paths, labels = self.scan_imgs_with_label(self.repo_path)

        @dataclass
        class HashIndexInfo:
            label: str
            hit: int = 0

        hash_index: dict[bytes, HashIndexInfo] = {
            h: HashIndexInfo(label=self.labels[i]) for i, h in enumerate(self.hashes)
        }

        deleted = 0
        label_mismatches: list[str] = []

        factory = make_progress or tqdm_factory
        bar = factory(len(image_paths), "扫描去重")
        for p, label in zip(image_paths, labels, strict=False):
            h = compute_file_hash(p)

            if h in hash_index:
                index_info = hash_index[h]

                if index_info.label != label:
                    label_mismatches.append(f"{index_info.label} != {label}: {p}")
                    continue

                index_info.hit += 1

                if index_info.hit > 1:
                    p.unlink()
                    deleted += 1
            bar.update(1)
        bar.close()

        return self.DeduplicateResult(deleted=deleted, label_mismatches=label_mismatches)

    @dataclass
    class ScanInitResult:
        ok: bool
        label_mismatches: list[str]

    def scan_init(
        self,
        repo_name: str,
        path: Path,
        extract_ccip: bool = False,
        extract_dreamsim: bool = False,
        *,
        make_progress: ProgressFactory | None = None,
    ) -> "ImageRepo.ScanInitResult":
        """初始化扫描一个已分类仓库"""
        image_paths, labels = self.scan_imgs_with_label(path)

        if len(image_paths) == 0:
            return self.ScanInitResult(ok=False, label_mismatches=[])

        hashes: list[bytes] = []
        valid_paths: list[Path] = []
        valid_labels: list[str] = []
        seen: dict[bytes, _SeenImage] = {}
        label_mismatches: list[str] = []

        factory = make_progress or tqdm_factory
        bar = factory(len(image_paths), "计算文件哈希")
        for p, label in zip(image_paths, labels, strict=False):
            h = compute_file_hash(p)
            if h not in seen:
                seen[h] = _SeenImage(p, label)
                hashes.append(h)
                valid_paths.append(p)
                valid_labels.append(label)
            elif seen[h].label != label:
                label_mismatches.append(f"{seen[h].label} != {label}: {p}")
            bar.update(1)
        bar.close()

        if not valid_paths:
            return self.ScanInitResult(ok=False, label_mismatches=label_mismatches)

        if extract_ccip:
            ccip_feats, _ = get_image_features_use_cache(
                "ccip",
                paths_and_hashes=PathsWithHashes(valid_paths, hashes),
                make_progress=make_progress,
            )
            self.ccip_features = np.stack(ccip_feats, axis=0)
        else:
            self.ccip_features = None

        if extract_dreamsim:
            ds_feats, _ = get_image_features_use_cache(
                "dreamsim",
                paths_and_hashes=PathsWithHashes(valid_paths, hashes),
                make_progress=make_progress,
            )
            self.dreamsim_features = np.stack(ds_feats, axis=0)
        else:
            self.dreamsim_features = None

        self.repo_name = repo_name
        self.repo_path = path
        self.hashes = hashes
        self.labels = valid_labels
        self.relative_paths = [p.relative_to(path).as_posix() for p in valid_paths]

        return self.ScanInitResult(ok=True, label_mismatches=label_mismatches)

    def _extract_missing_feature(
        self, feature_name: CacheName, hash_to_path: dict[bytes, Path], *, make_progress: ProgressFactory | None = None
    ) -> None:
        """为仓库中缺失指定特征的图片提取并更新特征"""
        assert self._repo_id is not None
        missing = self.missing_feature_hashes(feature_name)

        if not missing:
            return

        missing_hashes: list[bytes] = []
        missing_paths: list[Path] = []
        for h in missing:
            if h in hash_to_path:
                missing_hashes.append(h)
                missing_paths.append(hash_to_path[h])

        if not missing_paths:
            return

        features, _ = get_image_features_use_cache(
            feature_name,
            paths_and_hashes=PathsWithHashes(missing_paths, missing_hashes),
            make_progress=make_progress,
        )

        self.save_features(feature_name, missing_hashes, features)
