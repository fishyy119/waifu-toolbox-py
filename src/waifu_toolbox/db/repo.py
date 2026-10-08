# pyright: standard

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import numpy as np
from sqlalchemy import bindparam, delete, func, literal_column, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Connection

from ..utils.common import compute_file_hash, farthest_point_sampling
from ..utils.feature import PathsWithHashes, get_image_features_use_cache
from ..utils.image import IMG_EXTS
from ..utils.progress import ProgressFactory, tqdm_factory
from .cache import CacheManager, CacheName
from .schema import images, repos

if TYPE_CHECKING:
    from numpy.typing import NDArray


class FeatureStatus(NamedTuple):
    total: int
    ccip_count: int
    dreamsim_count: int


class ScanResult(NamedTuple):
    paths: list[Path]
    labels: list[str]


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
    def __init__(self, conn: Connection, repo_name: str | None = None):
        self._conn = conn
        self._cache = CacheManager(conn)
        self.ccip_features: NDArray[np.float32] | None = None
        self.dreamsim_features: NDArray[np.float32] | None = None
        self.hashes: list[bytes] = []
        self.labels: list[str] = []
        self.relative_paths: list[str] = []

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
        repo_id = self._conn.execute(
            select(repos.c.repo_id).where(repos.c.name == self._repo_name)
        ).scalar_one_or_none()
        if repo_id is None:
            raise ValueError(f"Repository '{self._repo_name}' not found")
        return repo_id

    def load(self, repo_name: str) -> bool:
        """加载仓库元数据与 hash/label 索引（不读取特征 BLOB）"""
        self._repo_name = repo_name

        row = self._conn.execute(select(repos.c.repo_id, repos.c.path).where(repos.c.name == repo_name)).one_or_none()
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
            select(images.c.hash, images.c.label, images.c.relative_path)
            .where(images.c.repo_id == self._repo_id)
            .order_by(literal_column("rowid"))
        ).all()

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
                select(images.c.hash, images.c.label, images.c.relative_path, images.c.ccip_feature)
                .where(images.c.repo_id == self._repo_id, images.c.ccip_feature.is_not(None))
                .order_by(literal_column("rowid"))
            ).all()
            self.hashes = [r[0] for r in rows]
            self.labels = [r[1] for r in rows]
            self.relative_paths = [r[2] or "" for r in rows]
            self.ccip_features = np.stack([np.frombuffer(r[3], dtype=np.float32) for r in rows]) if rows else None

        if dreamsim:
            rows = self._conn.execute(
                select(images.c.hash, images.c.label, images.c.relative_path, images.c.dreamsim_feature)
                .where(images.c.repo_id == self._repo_id, images.c.dreamsim_feature.is_not(None))
                .order_by(literal_column("rowid"))
            ).all()
            self.hashes = [r[0] for r in rows]
            self.labels = [r[1] for r in rows]
            self.relative_paths = [r[2] or "" for r in rows]
            self.dreamsim_features = np.stack([np.frombuffer(r[3], dtype=np.float32) for r in rows]) if rows else None

    def feature_status(self) -> FeatureStatus:
        """轻量查询特征覆盖状态"""
        assert self._repo_id is not None
        row = self._conn.execute(
            select(
                func.count(),
                func.count(images.c.ccip_feature),
                func.count(images.c.dreamsim_feature),
            ).where(images.c.repo_id == self._repo_id)
        ).one()
        return FeatureStatus(row[0], row[1], row[2])

    def save(self) -> None:
        assert self._repo_name is not None, "repo_name 未设置，无法保存"
        assert self.repo_path is not None, "repo_path 未设置，无法保存"

        repo_insert = sqlite_insert(repos)
        self._conn.execute(
            repo_insert.on_conflict_do_update(
                index_elements=[repos.c.name],
                set_={"path": repo_insert.excluded.path},
            ),
            {"name": self._repo_name, "path": str(self.repo_path)},
        )
        repo_id = self._conn.execute(select(repos.c.repo_id).where(repos.c.name == self._repo_name)).scalar_one()
        self._repo_id = repo_id

        image_rows = [
            {
                "repo_id": repo_id,
                "hash": image_hash,
                "label": label,
                "relative_path": self.relative_paths[i] if self.relative_paths else None,
                "ccip_feature": self.ccip_features[i].tobytes() if self.ccip_features is not None else None,
                "dreamsim_feature": (
                    self.dreamsim_features[i].tobytes() if self.dreamsim_features is not None else None
                ),
            }
            for i, (image_hash, label) in enumerate(zip(self.hashes, self.labels, strict=False))
        ]
        if image_rows:
            image_insert = sqlite_insert(images)
            self._conn.execute(
                image_insert.on_conflict_do_update(
                    index_elements=[images.c.repo_id, images.c.hash],
                    set_={
                        "label": image_insert.excluded.label,
                        "relative_path": image_insert.excluded.relative_path,
                        "ccip_feature": func.coalesce(image_insert.excluded.ccip_feature, images.c.ccip_feature),
                        "dreamsim_feature": func.coalesce(
                            image_insert.excluded.dreamsim_feature, images.c.dreamsim_feature
                        ),
                    },
                ),
                image_rows,
            )

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

        before_count = self._conn.execute(
            select(func.count()).select_from(images).where(images.c.repo_id == self._repo_id)
        ).scalar_one()

        if not existing_hashes:
            self._conn.execute(delete(images).where(images.c.repo_id == self._repo_id))
        else:
            # 临时表仅服务于当前连接上的批量差集删除，直接 SQL 比构造动态 Core Table 更清晰。
            self._conn.exec_driver_sql("CREATE TEMP TABLE IF NOT EXISTS _existing_hashes (hash BLOB PRIMARY KEY)")
            self._conn.exec_driver_sql("DELETE FROM _existing_hashes")
            self._conn.exec_driver_sql(
                "INSERT OR IGNORE INTO _existing_hashes (hash) VALUES (?)",
                [(image_hash,) for image_hash in existing_hashes],
            )
            self._conn.exec_driver_sql(
                """DELETE FROM images
                   WHERE repo_id = ? AND hash NOT IN
                       (SELECT hash FROM _existing_hashes)""",
                (self._repo_id,),
            )
            self._conn.exec_driver_sql("DROP TABLE IF EXISTS _existing_hashes")

        after_count = self._conn.execute(
            select(func.count()).select_from(images).where(images.c.repo_id == self._repo_id)
        ).scalar_one()

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

        hash_to_index: dict[bytes, int] = {h: i for i, h in enumerate(self.hashes)}
        hash_to_path: dict[bytes, Path] = {}
        updated_labels = 0
        new_entries: list[_ImageEntry] = []
        existing_updates: list[_ImageUpdate] = []

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
                existing_updates.append(_ImageUpdate(label, rel, h))
            else:
                new_entries.append(_ImageEntry(h, label, rel))
            bar.update(1)
        bar.close()

        if existing_updates:
            update_statement = (
                update(images)
                .where(
                    images.c.repo_id == bindparam("target_repo_id"),
                    images.c.hash == bindparam("target_hash"),
                )
                .values(
                    label=bindparam("new_label"),
                    relative_path=bindparam("new_relative_path"),
                )
            )
            self._conn.execute(
                update_statement,
                [
                    {
                        "new_label": entry.label,
                        "new_relative_path": entry.relative_path,
                        "target_repo_id": self._repo_id,
                        "target_hash": entry.hash,
                    }
                    for entry in existing_updates
                ],
            )
        if new_entries:
            self._conn.execute(
                images.insert(),
                [
                    {
                        "repo_id": self._repo_id,
                        "hash": entry.hash,
                        "label": entry.label,
                        "relative_path": entry.relative_path,
                    }
                    for entry in new_entries
                ],
            )

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
        self, feature_name: CacheName, hash_to_path: dict[bytes, Path], *, make_progress: ProgressFactory | None = None
    ) -> None:
        """为仓库中缺失指定特征的图片提取并更新特征"""
        assert self._repo_id is not None
        feature_column = {
            "ccip": images.c.ccip_feature,
            "dreamsim": images.c.dreamsim_feature,
        }[feature_name]

        missing = self._conn.execute(
            select(images.c.hash).where(images.c.repo_id == self._repo_id, feature_column.is_(None))
        ).all()

        if not missing:
            return

        missing_hashes: list[bytes] = []
        missing_paths: list[Path] = []
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

        update_statement = (
            update(images)
            .where(
                images.c.repo_id == bindparam("target_repo_id"),
                images.c.hash == bindparam("target_hash"),
            )
            .values({feature_column: bindparam("feature")})
        )
        self._conn.execute(
            update_statement,
            [
                {
                    "feature": feature.tobytes(),
                    "target_repo_id": self._repo_id,
                    "target_hash": image_hash,
                }
                for feature, image_hash in zip(features, missing_hashes, strict=False)
            ],
        )
