from pathlib import Path
from typing import List

from PIL import Image
from rich import print
from tqdm import tqdm


def collect_bmp_files(input_path: Path) -> List[Path]:
    if not input_path.exists():
        raise FileNotFoundError(f"{input_path} does not exist")

    if not input_path.is_dir():
        raise NotADirectoryError(f"{input_path} is not a directory")

    bmp_files = list(input_path.rglob("*.bmp"))
    print(f"Found {len(bmp_files)} BMP files in {input_path}")
    return bmp_files


def convert_images(input_path: Path, replace: bool = False):
    bmp_files = collect_bmp_files(input_path)
    converted = 0
    failed = 0

    for bmp_path in tqdm(bmp_files, desc="Converting BMP to WebP", unit="file", leave=False):
        try:
            webp_path = bmp_path.with_suffix(".webp")

            with Image.open(bmp_path) as img:
                # 统一转换为 RGB（避免部分 BMP 模式问题）
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")

                img.save(webp_path, "WEBP", quality=80, method=6)
                if replace:
                    bmp_path.unlink()  # 删除原 BMP 文件

            converted += 1

        except Exception as e:
            failed += 1
            print(f"[FAILED] {bmp_path} -> {e}")

    print(f"Converted: {converted}, Failed: [red]{failed}[/red]")
