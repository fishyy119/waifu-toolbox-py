# pyright: standard

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import numpy as np
from sqlalchemy import bindparam, delete, func, literal_column, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from . import connection as db_module
from .schema import images, repos

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from .cache import CacheName


class FeatureStatus(NamedTuple):
    total: int
    ccip_count: int
    dreamsim_count: int


class ImageEntry(NamedTuple):
    hash: bytes
    label: str
    relative_path: str


class ImageUpdate(NamedTuple):
    label: str
    relative_path: str
    hash: bytes


class RepoStorage:
    """读取和保存仓库索引，每次 SQL 操作独立管理连接。"""

    def __init__(self, repo_name: str | None = None):
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
        with db_module.database.connect() as conn:
            repo_id = conn.execute(select(repos.c.repo_id).where(repos.c.name == self._repo_name)).scalar_one_or_none()
            if repo_id is None:
                raise ValueError(f"Repository '{self._repo_name}' not found")
            return repo_id

    def load(self, repo_name: str) -> bool:
        """加载仓库元数据与 hash/label 索引（不读取特征 BLOB）"""
        with db_module.database.connect() as conn:
            self._repo_name = repo_name

            row = conn.execute(select(repos.c.repo_id, repos.c.path).where(repos.c.name == repo_name)).one_or_none()
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

            rows = conn.execute(
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
        with db_module.database.connect() as conn:
            assert self._repo_id is not None
            if not ccip and not dreamsim:
                return

            if ccip:
                rows = conn.execute(
                    select(images.c.hash, images.c.label, images.c.relative_path, images.c.ccip_feature)
                    .where(images.c.repo_id == self._repo_id, images.c.ccip_feature.is_not(None))
                    .order_by(literal_column("rowid"))
                ).all()
                self.hashes = [r[0] for r in rows]
                self.labels = [r[1] for r in rows]
                self.relative_paths = [r[2] or "" for r in rows]
                self.ccip_features = np.stack([np.frombuffer(r[3], dtype=np.float32) for r in rows]) if rows else None

            if dreamsim:
                rows = conn.execute(
                    select(images.c.hash, images.c.label, images.c.relative_path, images.c.dreamsim_feature)
                    .where(images.c.repo_id == self._repo_id, images.c.dreamsim_feature.is_not(None))
                    .order_by(literal_column("rowid"))
                ).all()
                self.hashes = [r[0] for r in rows]
                self.labels = [r[1] for r in rows]
                self.relative_paths = [r[2] or "" for r in rows]
                self.dreamsim_features = (
                    np.stack([np.frombuffer(r[3], dtype=np.float32) for r in rows]) if rows else None
                )

    def feature_status(self) -> FeatureStatus:
        """轻量查询特征覆盖状态"""
        with db_module.database.connect() as conn:
            assert self._repo_id is not None
            row = conn.execute(
                select(
                    func.count(),
                    func.count(images.c.ccip_feature),
                    func.count(images.c.dreamsim_feature),
                ).where(images.c.repo_id == self._repo_id)
            ).one()
            return FeatureStatus(row[0], row[1], row[2])

    def save(self, *, create_only: bool = False) -> bool:
        with db_module.database.begin() as conn:
            assert self._repo_name is not None, "repo_name 未设置，无法保存"
            assert self.repo_path is not None, "repo_path 未设置，无法保存"

            repo_insert = sqlite_insert(repos)
            if create_only:
                # 扫描期间可能有其他进程创建同名仓库，提交时再次保护已有索引。
                repo_id = conn.execute(
                    repo_insert.on_conflict_do_nothing(index_elements=[repos.c.name]).returning(repos.c.repo_id),
                    {"name": self._repo_name, "path": str(self.repo_path)},
                ).scalar_one_or_none()
                if repo_id is None:
                    return False
            else:
                conn.execute(
                    repo_insert.on_conflict_do_update(
                        index_elements=[repos.c.name],
                        set_={"path": repo_insert.excluded.path},
                    ),
                    {"name": self._repo_name, "path": str(self.repo_path)},
                )
                repo_id = conn.execute(select(repos.c.repo_id).where(repos.c.name == self._repo_name)).scalar_one()
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
                conn.execute(
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
            return True

    def purge_except(self, existing_hashes: set[bytes]) -> int:
        """删除当前仓库中不在现有 hash 集合内的索引。"""
        assert self._repo_id is not None
        with db_module.database.begin() as conn:
            before_count = conn.execute(
                select(func.count()).select_from(images).where(images.c.repo_id == self._repo_id)
            ).scalar_one()

            if not existing_hashes:
                conn.execute(delete(images).where(images.c.repo_id == self._repo_id))
            else:
                # 临时表仅服务于当前连接上的批量差集删除，直接 SQL 比构造动态 Core Table 更清晰。
                conn.exec_driver_sql("CREATE TEMP TABLE IF NOT EXISTS _existing_hashes (hash BLOB PRIMARY KEY)")
                conn.exec_driver_sql("DELETE FROM _existing_hashes")
                conn.exec_driver_sql(
                    "INSERT OR IGNORE INTO _existing_hashes (hash) VALUES (?)",
                    [(image_hash,) for image_hash in existing_hashes],
                )
                conn.exec_driver_sql(
                    """DELETE FROM images
                       WHERE repo_id = ? AND hash NOT IN
                           (SELECT hash FROM _existing_hashes)""",
                    (self._repo_id,),
                )
                conn.exec_driver_sql("DROP TABLE IF EXISTS _existing_hashes")

            after_count = conn.execute(
                select(func.count()).select_from(images).where(images.c.repo_id == self._repo_id)
            ).scalar_one()

            return before_count - after_count

    def sync_entries(self, new_entries: list[ImageEntry], existing_updates: list[ImageUpdate]) -> None:
        """批量提交扫描后得到的新增索引和路径、标签变化。"""
        assert self._repo_id is not None
        with db_module.database.begin() as conn:
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
                conn.execute(
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
                conn.execute(
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

    def missing_feature_hashes(self, feature_name: CacheName) -> list[bytes]:
        """查询尚未保存指定特征的图片 hash。"""
        assert self._repo_id is not None
        feature_column = {
            "ccip": images.c.ccip_feature,
            "dreamsim": images.c.dreamsim_feature,
        }[feature_name]

        with db_module.database.connect() as conn:
            missing = conn.execute(
                select(images.c.hash).where(images.c.repo_id == self._repo_id, feature_column.is_(None))
            ).all()
        return [row[0] for row in missing]

    def save_features(self, feature_name: CacheName, hashes: list[bytes], features: list[NDArray[np.float32]]) -> None:
        """批量保存指定图片的特征向量。"""
        assert self._repo_id is not None
        feature_column = {
            "ccip": images.c.ccip_feature,
            "dreamsim": images.c.dreamsim_feature,
        }[feature_name]

        with db_module.database.begin() as conn:
            update_statement = (
                update(images)
                .where(
                    images.c.repo_id == bindparam("target_repo_id"),
                    images.c.hash == bindparam("target_hash"),
                )
                .values({feature_column: bindparam("feature")})
            )
            conn.execute(
                update_statement,
                [
                    {
                        "feature": feature.tobytes(),
                        "target_repo_id": self._repo_id,
                        "target_hash": image_hash,
                    }
                    for feature, image_hash in zip(features, hashes, strict=False)
                ],
            )
