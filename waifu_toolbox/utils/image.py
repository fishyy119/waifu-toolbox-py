import random
import warnings
from pathlib import Path
from typing import List, Tuple

import numpy as np
from numpy.typing import NDArray
from PIL import Image
from PIL.Image import Image as ImageType
from tqdm import tqdm

from .cache import CacheManager
from .common import compute_file_hash

warnings.filterwarnings("ignore", "Corrupt EXIF data")


def get_image_features_use_cache(
    img_folder_root: Path | None = None,
    paths_and_hashes: Tuple[List[Path], List[bytes]] | None = None,
) -> Tuple[List[NDArray[np.float32]], List[Path]]:
    """获取指定文件夹下所有图片的特征，考虑缓存"""
    features = []
    img_paths = []
    img_hashes = []
    if img_folder_root is not None:
        exts = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif")
        for ext in exts:
            img_paths.extend(img_folder_root.rglob(ext))
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
        feature = cache.get("ccip", img_hash)
        if feature is not None:
            features.append(feature)
            tqdm_feature.update(1)
        else:
            extract_quene.append((img_idx, load_image(img_path)))
            features.append(None)  # 占位符
            tqdm_feature.update(0.1)

    # 统一提取速度更快
    for img_idx, img in extract_quene:
        feature = ccip_extract_feature(img)
        features[img_idx] = feature
        cache.set("ccip", img_hashes[img_idx], feature)
        tqdm_feature.update(0.9)

    tqdm_feature.close()
    cache.save_cache("ccip")
    return features, img_paths


def load_image(path: Path, max_size: int | Tuple[int, int] = 256) -> ImageType:
    """读取单张图片"""
    img = Image.open(path).convert("RGBA")
    if isinstance(max_size, int):
        max_size = (max_size, max_size)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    return img


def load_images_from_folder(
    folder: Path,
    max_samples: int | None = None,
    max_sample_rate: float | None = None,
    tqdm_title: str | None = None,
) -> Tuple[List[ImageType], List[Path]]:
    """
    分层采样读取图片（根目录及一级子目录），采样总数由 max_samples 或 max_sample_rate 控制

    参数:
        folder: 根目录
        max_samples: 最大采样总数
        max_sample_rate: 最大采样比例 (0-1)

    返回:
        images: ImageType 列表
        file_paths: 对应路径列表
    """
    exts = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif")
    all_groups: List[List[Path]] = []

    # 收集所有子目录和根目录的图片
    # 根目录视为特殊子目录
    root_files = []
    for ext in exts:
        root_files.extend(folder.glob(ext))
    if root_files:
        all_groups.append(root_files)

    # 一级子目录
    for subdir in folder.iterdir():
        if not subdir.is_dir():
            continue
        sub_files = []
        for ext in exts:
            sub_files.extend(subdir.rglob(ext))
        if sub_files:
            all_groups.append(sub_files)

    # 计算总样本数限制
    total_files = sum(len(g) for g in all_groups)
    if max_samples is not None:
        total_sample_num = min(total_files, max_samples)
    elif max_sample_rate is not None:
        total_sample_num = int(total_files * max_sample_rate)
    else:
        total_sample_num = total_files

    # 分配每个子组采样数（按比例）
    sampled_files: List[Path] = []
    for group in all_groups:
        group_sample_num = int(len(group) / total_files * total_sample_num)
        group_sample_num = min(group_sample_num, len(group))
        if group_sample_num > 0:
            sampled_files.extend(random.sample(group, group_sample_num))

    # 读取图片
    images: List[ImageType] = []
    if tqdm_title:
        from tqdm import tqdm

        iterator = tqdm(sampled_files, desc=tqdm_title, unit="img")
    else:
        iterator = sampled_files

    for file_path in iterator:
        images.append(load_image(file_path, 256))

    return images, sampled_files
