from pathlib import Path
from typing import Any, Dict, Literal, Optional

import numpy as np
from numpy.typing import NDArray

CACHE_ROOT = Path(__file__).parents[2] / "database/cache"
CACHE_ROOT.mkdir(exist_ok=True, parents=True)


CCIP_Feature = NDArray[np.float32]
CacheName = Literal["ccip"]
FeatureType = CCIP_Feature
# LPIPS的特征极大（100个/GB），是直接提取的CNN参数，不具备保存条件


class CacheManager:
    """
    通用缓存管理器
    - 支持多种特征类型，每种特征对应单独缓存文件
    - 使用 hash 作为 key 查询特征
    """

    def __init__(self):
        self.caches: Dict[CacheName, Dict[bytes, FeatureType]] = {}  # 内存字典

    def _get_cache_path(self, feature_name: CacheName) -> Path:
        return CACHE_ROOT / f"{feature_name}.npz"

    def load_cache(self, feature_name: CacheName) -> None:
        """读取指定特征类型的缓存"""
        path = self._get_cache_path(feature_name)
        if path.exists():
            data = np.load(path, allow_pickle=True)
            hashes_np = data["hashes"]
            features_np = data["features"]
            # bytes 作为 key，NDArray 作为 value
            self.caches[feature_name] = {
                h.tobytes() if isinstance(h, np.void) else h: f for h, f in zip(hashes_np, features_np)
            }
        else:
            self.caches[feature_name] = {}

    def save_cache(self, feature_name: CacheName) -> None:
        """保存指定特征类型的缓存"""
        if feature_name not in self.caches:
            return
        cache_dict = self.caches[feature_name]
        hashes_np = np.array(list(cache_dict.keys()), dtype=np.object_)
        features_np = np.array(list(cache_dict.values()))
        np.savez_compressed(self._get_cache_path(feature_name), hashes=hashes_np, features=features_np)

    def get(self, feature_name: CacheName, hash_key: bytes) -> Optional[Any]:
        """按 hash 查询特征，如果命中返回特征，否则返回 None"""
        if feature_name not in self.caches:
            self.load_cache(feature_name)
        return self.caches[feature_name].get(hash_key, None)

    def set(self, feature_name: CacheName, hash_key: bytes, value: Any) -> None:
        """将特征存入缓存"""
        if feature_name not in self.caches:
            self.load_cache(feature_name)
        self.caches[feature_name][hash_key] = value

    def has(self, feature_name: CacheName, hash_key: bytes) -> bool:
        """判断特征是否已缓存"""
        if feature_name not in self.caches:
            self.load_cache(feature_name)
        return hash_key in self.caches[feature_name]
