import sqlite3
from typing import Dict, Literal, TypeAlias

import numpy as np
from numpy.typing import NDArray

CacheName: TypeAlias = Literal["ccip", "dreamsim"]
FeatureType: TypeAlias = NDArray[np.float32]


class CacheManager:
    """
    通用缓存管理器
    - 读取走 SQLite 点查，不全量加载
    - 写入先缓冲到内存，调用 save_cache 时批量写入
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._dirty: Dict[CacheName, Dict[bytes, FeatureType]] = {}

    def get(self, feature_name: CacheName, hash_key: bytes) -> FeatureType | None:
        """按 hash 查询特征，如果命中返回特征，否则返回 None"""
        if feature_name in self._dirty and hash_key in self._dirty[feature_name]:
            return self._dirty[feature_name][hash_key]
        row = self._conn.execute(
            """SELECT feature FROM feature_cache
               WHERE hash = ? AND feature_type = ?""",
            (hash_key, feature_name),
        ).fetchone()
        if row is None:
            return None
        return np.frombuffer(row[0], dtype=np.float32).copy()

    def set(self, feature_name: CacheName, hash_key: bytes, value: FeatureType) -> None:
        """将特征存入写缓冲"""
        self._dirty.setdefault(feature_name, {})[hash_key] = np.asarray(value, dtype=np.float32)

    def save_cache(self, feature_name: CacheName) -> None:
        """将缓冲的特征批量写入数据库"""
        if feature_name not in self._dirty or not self._dirty[feature_name]:
            return
        dirty = self._dirty[feature_name]
        with self._conn:
            self._conn.executemany(
                """INSERT OR REPLACE INTO feature_cache (hash, feature_type, feature)
                   VALUES (?, ?, ?)""",
                [(h, feature_name, v.tobytes()) for h, v in dirty.items()],
            )
        dirty.clear()
