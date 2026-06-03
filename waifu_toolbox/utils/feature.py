# pyright: standard

from pathlib import Path
from typing import List, Tuple, cast

import numpy as np
from numpy.typing import NDArray
from PIL.Image import Image as ImageType
from tqdm import tqdm

from ..db.cache import CCIP_Feature, CacheManager, CacheName
from .common import compute_file_hash
from .image import IMG_EXTS, load_image


def get_image_features_use_cache(
    feature_name: CacheName,
    img_folder_root: Path | None = None,
    paths_and_hashes: Tuple[List[Path], List[bytes]] | None = None,
    recursive: bool = True,
) -> Tuple[List[NDArray[np.float32]], List[Path]]:
    """获取指定文件夹下所有图片的特征，考虑缓存"""
    features: List[CCIP_Feature | None] = []
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
        img_paths, img_hashes = paths_and_hashes
    else:
        raise ValueError("必须指定 img_folder_root 或 image_paths 参数")

    cache = CacheManager()
    from imgutils.metrics.ccip import ccip_extract_feature

    tqdm_feature = tqdm(total=len(img_paths), desc="提取图片特征", unit="img")
    extract_quene: List[Tuple[int, ImageType]] = []
    for img_idx, (img_path, img_hash) in enumerate(zip(img_paths, img_hashes)):
        cached_feature = cast(CCIP_Feature | None, cache.get(feature_name, img_hash))
        if cached_feature is not None:
            features.append(cached_feature)
            tqdm_feature.update(1)
        else:
            extract_quene.append((img_idx, load_image(img_path)))
            features.append(None)  # 占位符
            tqdm_feature.update(0.1)

    # 统一提取速度更快
    for img_idx, img in extract_quene:
        feature = cast(CCIP_Feature, ccip_extract_feature(img))
        features[img_idx] = feature
        cache.set(feature_name, img_hashes[img_idx], feature)
        tqdm_feature.update(0.9)

    tqdm_feature.close()
    cache.save_cache(feature_name)
    return cast(List[NDArray[np.float32]], features), img_paths
