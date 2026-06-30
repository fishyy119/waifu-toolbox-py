# pyright: standard

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, NamedTuple, Sequence, cast

import numpy as np
from numpy.typing import NDArray

from ..db.cache import CacheManager, CacheName, FeatureType
from .common import compute_file_hash
from .dreamsim import extract_dreamsim_embedding_from_path
from .image import IMG_EXTS, load_image
from .progress import ProgressFactory, tqdm_factory


@dataclass(frozen=True)
class PathsWithHashes:
    paths: Sequence[Path]
    hashes: Sequence[bytes]

    def __post_init__(self) -> None:
        if len(self.paths) != len(self.hashes):
            raise ValueError("图片路径与哈希数量不一致")


class FeatureResult(NamedTuple):
    features: List[NDArray[np.float32]]
    paths: List[Path]


def _extract_ccip_feature(img_path: Path) -> FeatureType:
    from imgutils.metrics.ccip import ccip_extract_feature

    return np.asarray(ccip_extract_feature(load_image(img_path)), dtype=np.float32)


def _get_feature_extractor(feature_name: CacheName) -> Callable[[Path], FeatureType]:
    if feature_name == "ccip":
        return _extract_ccip_feature
    if feature_name == "dreamsim":
        return extract_dreamsim_embedding_from_path
    raise ValueError(f"不支持的特征类型: {feature_name}")


def get_image_features_use_cache(
    feature_name: CacheName,
    img_folder_root: Path | None = None,
    paths_and_hashes: PathsWithHashes | None = None,
    recursive: bool = True,
    *,
    cache: CacheManager,
    make_progress: ProgressFactory | None = None,
) -> FeatureResult:
    """获取指定文件夹下所有图片的特征，考虑缓存"""
    features: List[FeatureType | None] = []
    img_paths: List[Path] = []
    img_hashes: List[bytes] = []
    if img_folder_root is not None:
        exts = IMG_EXTS
        for ext in exts:
            if recursive:
                img_paths.extend(img_folder_root.rglob(ext))
            else:
                img_paths.extend(img_folder_root.glob(ext))
        img_hashes = [compute_file_hash(p) for p in img_paths]
    elif paths_and_hashes is not None:
        img_paths = list(paths_and_hashes.paths)
        img_hashes = list(paths_and_hashes.hashes)
    else:
        raise ValueError("必须指定 img_folder_root 或 image_paths 参数")

    extractor = _get_feature_extractor(feature_name)

    factory = make_progress or tqdm_factory
    bar = factory(len(img_paths), "提取图片特征")
    extract_queue: List[int] = []
    for img_idx, (img_path, img_hash) in enumerate(zip(img_paths, img_hashes)):
        cached_feature = cache.get(feature_name, img_hash)
        if cached_feature is not None:
            features.append(cached_feature)
            bar.update(1)
        else:
            extract_queue.append(img_idx)
            features.append(None)  # 占位符

    for img_idx in extract_queue:
        feature = extractor(img_paths[img_idx])
        features[img_idx] = feature
        cache.set(feature_name, img_hashes[img_idx], feature)
        bar.update(1)

    bar.close()
    cache.save_cache(feature_name)
    features_casted = cast(List[FeatureType], features)
    return FeatureResult(features_casted, img_paths)
