# pyright: standard

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, NamedTuple, Set

import numpy as np
from numpy.typing import NDArray

from ..utils.common import compute_file_hash, farthest_point_sampling
from ..utils.feature import PathsWithHashes, get_image_features_use_cache
from ..utils.image import IMG_EXTS
from ..utils.progress import ProgressFactory, tqdm_factory
from .cache import CacheManager, CacheName


class FeatureStatus(NamedTuple):
    total: int
    ccip_count: int
    dreamsim_count: int


class ScanResult(NamedTuple):
    paths: List[Path]
    labels: List[str]


class _ImageEntry(NamedTuple):
    hash: bytes
    label: str
    relative_path: str


class _ImageUpdate(NamedTuple):
    label: str
    relative_path: str
    hash: bytes


class _SeenImage(NamedTuple):
    path: Path
    label: str


class ImageRepo:
    def __init__(self, conn: sqlite3.Connection, repo_name: str | None = None):
        self._conn = conn
        self._cache = CacheManager(conn)
        self.ccip_features: NDArray[np.float32] | None = None
        self.dreamsim_features: NDArray[np.float32] | None = None
        self.hashes: List[bytes] = []
        self.labels: List[str] = []
        self.relative_paths: List[str] = []

        self._repo_name: str | None = None
        self._repo_id: int | None = None
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
    def repo_name(self, name: str) -> None:
        self._repo_name = name

    def _resolve_repo_id(self) -> int:
        row = self._conn.execute(
            """SELECT repo_id FROM repos WHERE name = ?""",
            (self._repo_name,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Repository '{self._repo_name}' not found")
        return row[0]

    def load(self, repo_name: str) -> bool:
        """加载仓库元数据与 hash/label 索引（不读取特征 BLOB）"""
        self._repo_name = repo_name

        row = self._conn.execute(
            """SELECT repo_id, path FROM repos WHERE name = ?""",
            (repo_name,),
        ).fetchone()
        if row is None:
            self.ccip_features = None
            self.dreamsim_features = None
            self.hashes = []
            self.labels = []
            self.relative_paths = []
            self.repo_path = None
            self._repo_id = None
            return False

        self._repo_id = row[0]
        self.repo_path = Path(row[1])

        rows = self._conn.execute(
            """SELECT hash, label, relative_path FROM images
               WHERE repo_id = ? ORDER BY rowid""",
            (self._repo_id,),
        ).fetchall()

        self.hashes = [r[0] for r in rows]
        self.labels = [r[1] for r in rows]
        self.relative_paths = [r[2] or "" for r in rows]
        self.ccip_features = None
        self.dreamsim_features = None

        return True

    def load_features(self, ccip: bool = False, dreamsim: bool = False) -> None:
        """按需加载特征向量，过滤为拥有所请求特征的子集，hashes/labels 同步收窄"""
        assert self._repo_id is not None
        if not ccip and not dreamsim:
            return

        if ccip:
            rows = self._conn.execute(
                """SELECT hash, label, relative_path, ccip_feature FROM images
                   WHERE repo_id = ? AND ccip_feature IS NOT NULL
                   ORDER BY rowid""",
                (self._repo_id,),
            ).fetchall()
            self.hashes = [r[0] for r in rows]
            self.labels = [r[1] for r in rows]
            self.relative_paths = [r[2] or "" for r in rows]
            self.ccip_features = np.stack([np.frombuffer(r[3], dtype=np.float32) for r in rows]) if rows else None

        if dreamsim:
            rows = self._conn.execute(
                """SELECT hash, label, relative_path, dreamsim_feature FROM images
                   WHERE repo_id = ? AND dreamsim_feature IS NOT NULL
                   ORDER BY rowid""",
                (self._repo_id,),
            ).fetchall()
            self.hashes = [r[0] for r in rows]
            self.labels = [r[1] for r in rows]
            self.relative_paths = [r[2] or "" for r in rows]
            self.dreamsim_features = np.stack([np.frombuffer(r[3], dtype=np.float32) for r in rows]) if rows else None

    def feature_status(self) -> FeatureStatus:
        """轻量查询特征覆盖状态"""
        assert self._repo_id is not None
        row = self._conn.execute(
            """SELECT COUNT(*), COUNT(ccip_feature), COUNT(dreamsim_feature)
               FROM images WHERE repo_id = ?""",
            (self._repo_id,),
        ).fetchone()
        return FeatureStatus(row[0], row[1], row[2])

    def save(self) -> None:
        assert self._repo_name is not None, "repo_name 未设置，无法保存"
        assert self.repo_path is not None, "repo_path 未设置，无法保存"

        with self._conn:
            self._conn.execute(
                """INSERT INTO repos (name, path) VALUES (?, ?)
                   ON CONFLICT(name) DO UPDATE SET path = excluded.path""",
                (self._repo_name, str(self.repo_path)),
            )
            repo_id: int = self._conn.execute(
                """SELECT repo_id FROM repos WHERE name = ?""",
                (self._repo_name,),
            ).fetchone()[0]
            self._repo_id = repo_id

            self._conn.executemany(
                """INSERT INTO images (repo_id, hash, label, relative_path, ccip_feature, dreamsim_feature)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(repo_id, hash) DO UPDATE SET
                       label = excluded.label,
                       relative_path = excluded.relative_path,
                       ccip_feature = COALESCE(excluded.ccip_feature, images.ccip_feature),
                       dreamsim_feature = COALESCE(excluded.dreamsim_feature, images.dreamsim_feature)""",
                [
                    (
                        repo_id,
                        h,
                        label,
                        self.relative_paths[i] if self.relative_paths else None,
                        self.ccip_features[i].tobytes() if self.ccip_features is not None else None,
                        self.dreamsim_features[i].tobytes() if self.dreamsim_features is not None else None,
                    )
                    for i, (h, label) in enumerate(zip(self.hashes, self.labels))
                ],
            )

    def sample(self, max_num: int) -> None:
        """
        从每个类别中随机采样最多 max_num 个样本，用于分类参考。
        会就地覆盖 features / hashes / labels。
        """
        assert self.ccip_features is not None
        assert len(self.ccip_features) == len(self.labels) == len(self.hashes)

        label_to_indices: Dict[str, List[int]] = defaultdict(list)
        for idx, label in enumerate(self.labels):
            label_to_indices[label].append(idx)

        selected_indices: List[int] = []
        for label, indices in label_to_indices.items():
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

        return ScanResult(image_paths, labels)

    def purge(self, name: str, *, make_progress: ProgressFactory | None = None) -> int:
        """移除索引中已经不存在于磁盘的图片记录，返回删除数量"""
        self.load(name)
        assert self.repo_path is not None
        assert self._repo_id is not None

        image_paths, _ = self.scan_imgs_with_label(self.repo_path)
        existing_hashes: Set[bytes] = set()

        factory = make_progress or tqdm_factory
        bar = factory(len(image_paths), "计算现有文件哈希")
        for p in image_paths:
            h = compute_file_hash(p)
            existing_hashes.add(h)
            bar.update(1)
        bar.close()

        with self._conn:
            before_count = self._conn.execute(
                """SELECT COUNT(*) FROM images WHERE repo_id = ?""",
                (self._repo_id,),
            ).fetchone()[0]

            if not existing_hashes:
                self._conn.execute(
                    """DELETE FROM images WHERE repo_id = ?""",
                    (self._repo_id,),
                )
            else:
                self._conn.execute("""CREATE TEMP TABLE IF NOT EXISTS _existing_hashes
                       (hash BLOB PRIMARY KEY)""")
                self._conn.execute("""DELETE FROM _existing_hashes""")
                self._conn.executemany(
                    """INSERT OR IGNORE INTO _existing_hashes (hash) VALUES (?)""",
                    [(h,) for h in existing_hashes],
                )
                self._conn.execute(
                    """DELETE FROM images
                       WHERE repo_id = ? AND hash NOT IN
                           (SELECT hash FROM _existing_hashes)""",
                    (self._repo_id,),
                )
                self._conn.execute("""DROP TABLE IF EXISTS _existing_hashes""")

            after_count = self._conn.execute(
                """SELECT COUNT(*) FROM images WHERE repo_id = ?""",
                (self._repo_id,),
            ).fetchone()[0]

        return before_count - after_count

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

        hash_to_index: Dict[bytes, int] = {h: i for i, h in enumerate(self.hashes)}
        hash_to_path: Dict[bytes, Path] = {}
        updated_labels = 0
        new_entries: List[_ImageEntry] = []
        existing_updates: List[_ImageUpdate] = []

        factory = make_progress or tqdm_factory
        bar = factory(len(image_paths), "扫描并同步索引")
        for p, label in zip(image_paths, labels):
            h = compute_file_hash(p)
            hash_to_path[h] = p
            rel = str(p.relative_to(self.repo_path))

            if h in hash_to_index:
                idx = hash_to_index[h]
                if self.labels[idx] != label:
                    updated_labels += 1
                existing_updates.append(_ImageUpdate(label, rel, h))
            else:
                new_entries.append(_ImageEntry(h, label, rel))
            bar.update(1)
        bar.close()

        with self._conn:
            if existing_updates:
                self._conn.executemany(
                    """UPDATE images SET label = ?, relative_path = ?
                       WHERE repo_id = ? AND hash = ?""",
                    [(e.label, e.relative_path, self._repo_id, e.hash) for e in existing_updates],
                )
            if new_entries:
                self._conn.executemany(
                    """INSERT INTO images (repo_id, hash, label, relative_path)
                       VALUES (?, ?, ?, ?)""",
                    [(self._repo_id, e.hash, e.label, e.relative_path) for e in new_entries],
                )

        if extract_ccip:
            self._extract_missing_feature("ccip", hash_to_path, make_progress=make_progress)
        if extract_dreamsim:
            self._extract_missing_feature("dreamsim", hash_to_path, make_progress=make_progress)

        return self.UpdateResult(new_images=len(new_entries), updated_labels=updated_labels)

    @dataclass
    class DeduplicateResult:
        deleted: int
        label_mismatches: List[str]

    def deduplicate(self, name: str, *, make_progress: ProgressFactory | None = None) -> "ImageRepo.DeduplicateResult":
        """基于文件hash去重仓库中的重复图片，返回去重结果"""
        self.load(name)
        assert self.repo_path is not None

        image_paths, labels = self.scan_imgs_with_label(self.repo_path)

        @dataclass
        class HashIndexInfo:
            label: str
            hit: int = 0

        hash_index: Dict[bytes, HashIndexInfo] = {
            h: HashIndexInfo(label=self.labels[i]) for i, h in enumerate(self.hashes)
        }

        deleted = 0
        label_mismatches: List[str] = []

        factory = make_progress or tqdm_factory
        bar = factory(len(image_paths), "扫描去重")
        for p, label in zip(image_paths, labels):
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
        label_mismatches: List[str]

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

        hashes: List[bytes] = []
        valid_paths: List[Path] = []
        valid_labels: List[str] = []
        seen: Dict[bytes, _SeenImage] = {}
        label_mismatches: List[str] = []

        factory = make_progress or tqdm_factory
        bar = factory(len(image_paths), "计算文件哈希")
        for p, label in zip(image_paths, labels):
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
                cache=self._cache,
                make_progress=make_progress,
            )
            self.ccip_features = np.stack(ccip_feats, axis=0)
        else:
            self.ccip_features = None

        if extract_dreamsim:
            ds_feats, _ = get_image_features_use_cache(
                "dreamsim",
                paths_and_hashes=PathsWithHashes(valid_paths, hashes),
                cache=self._cache,
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
        self, feature_name: CacheName, hash_to_path: Dict[bytes, Path], *, make_progress: ProgressFactory | None = None
    ) -> None:
        """为仓库中缺失指定特征的图片提取并更新特征"""
        assert self._repo_id is not None
        column = {"ccip": "ccip_feature", "dreamsim": "dreamsim_feature"}[feature_name]

        missing = self._conn.execute(
            f"""SELECT hash FROM images
                WHERE repo_id = ? AND {column} IS NULL""",
            (self._repo_id,),
        ).fetchall()

        if not missing:
            return

        missing_hashes: List[bytes] = []
        missing_paths: List[Path] = []
        for (h,) in missing:
            if h in hash_to_path:
                missing_hashes.append(h)
                missing_paths.append(hash_to_path[h])

        if not missing_paths:
            return

        features, _ = get_image_features_use_cache(
            feature_name,
            paths_and_hashes=PathsWithHashes(missing_paths, missing_hashes),
            cache=self._cache,
            make_progress=make_progress,
        )

        with self._conn:
            self._conn.executemany(
                f"""UPDATE images SET {column} = ?
                    WHERE repo_id = ? AND hash = ?""",
                [(f.tobytes(), self._repo_id, h) for f, h in zip(features, missing_hashes)],
            )
