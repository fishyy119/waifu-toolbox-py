from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

from PIL import Image
from rich import print
from tqdm import tqdm


def convert_single(source_path: Path, replace: bool):
    webp_path = source_path.with_suffix(".webp")
    try:
        with Image.open(source_path) as img:
            if img.mode == "P":
                if "transparency" in img.info:
                    img = img.convert("RGBA")
                else:
                    img = img.convert("RGB")
            elif img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")

            img.save(webp_path, "WEBP", quality=85, method=6)

            if replace:
                source_path.unlink()
        return True
    except Exception as e:
        print(f"[FAILED] {source_path} -> {e}")
        return False


def convert_images_parallel(source_files: List[Path], replace: bool = False):
    converted = 0
    failed = 0

    with ThreadPoolExecutor() as executor:
        futures: List[Future[bool]] = [executor.submit(convert_single, p, replace) for p in source_files]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Converting images", unit="file"):
            if future.result():
                converted += 1
            else:
                failed += 1

    print(f"Converted: {converted}, Failed: [red]{failed}[/red]")


def collect_files(input_path: Path, ext: str) -> List[Path]:
    if not input_path.exists():
        raise FileNotFoundError(f"{input_path} does not exist")

    if not input_path.is_dir():
        raise NotADirectoryError(f"{input_path} is not a directory")

    files = list(input_path.rglob(ext))
    print(f"Found {len(files)} files in {input_path} with extension {ext}")
    return files


def convert_images(input_path: Path, replace: bool = False, source_format: str = "bmp"):
    source_files = collect_files(input_path, ext=f"*.{source_format.lower()}")
    convert_images_parallel(source_files, replace=replace)
