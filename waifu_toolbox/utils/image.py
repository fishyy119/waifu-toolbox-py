import random
import warnings
from pathlib import Path
from typing import List, Tuple

from PIL import Image
from PIL.Image import Image as ImageType

warnings.filterwarnings("ignore", "Corrupt EXIF data")
IMG_EXTS = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif", "*.webp")


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
    exts = IMG_EXTS
    all_groups: List[List[Path]] = []

    # 收集所有子目录和根目录的图片
    # 根目录视为特殊子目录
    root_files: List[Path] = []
    for ext in exts:
        root_files.extend(folder.glob(ext))
    if root_files:
        all_groups.append(root_files)

    # 一级子目录
    for subdir in folder.iterdir():
        if not subdir.is_dir():
            continue
        sub_files: List[Path] = []
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
