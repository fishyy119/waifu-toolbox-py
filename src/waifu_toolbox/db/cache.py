from typing import Literal

import numpy as np
from numpy.typing import NDArray
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Connection

from .schema import feature_cache

type CacheName = Literal["ccip", "dreamsim"]
type FeatureType = NDArray[np.float32]


class CacheManager:
    """
    通用缓存管理器
    - 读取走 SQLite 点查，不全量加载
    - 写入先缓冲到内存，调用 save_cache 时批量写入
    """

    def __init__(self, conn: Connection) -> None:
        self._conn = conn
        self._dirty: dict[CacheName, dict[bytes, FeatureType]] = {}

    def get(self, feature_name: CacheName, hash_key: bytes) -> FeatureType | None:
        """按 hash 查询特征，如果命中返回特征，否则返回 None"""
        if feature_name in self._dirty and hash_key in self._dirty[feature_name]:
            return self._dirty[feature_name][hash_key]
        feature = self._conn.execute(
            select(feature_cache.c.feature).where(
                feature_cache.c.hash == hash_key,
                feature_cache.c.feature_type == feature_name,
            )
        ).scalar_one_or_none()
        if feature is None:
            return None
        return np.frombuffer(feature, dtype=np.float32).copy()

    def set(self, feature_name: CacheName, hash_key: bytes, value: FeatureType) -> None:
        """将特征存入写缓冲"""
        self._dirty.setdefault(feature_name, {})[hash_key] = np.asarray(value, dtype=np.float32)

    def save_cache(self, feature_name: CacheName) -> None:
        """将缓冲的特征批量写入数据库"""
        if feature_name not in self._dirty or not self._dirty[feature_name]:
            return
        dirty = self._dirty[feature_name]
        insert_statement = sqlite_insert(feature_cache)
        upsert_statement = insert_statement.on_conflict_do_update(
            index_elements=[feature_cache.c.hash, feature_cache.c.feature_type],
            set_={"feature": insert_statement.excluded.feature},
        )
        self._conn.execute(
            upsert_statement,
            [
                {"hash": hash_key, "feature_type": feature_name, "feature": value.tobytes()}
                for hash_key, value in dirty.items()
            ],
        )
        dirty.clear()
