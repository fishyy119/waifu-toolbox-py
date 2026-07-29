from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from ..utils.progress import ProgressFactory, tqdm_factory
from ..utils.result import Result


@dataclass
class ConvertResult:
    converted: int
    failed: int
    errors: list[str] = field(default_factory=lambda: [])


def convert_single(source_path: Path, replace: bool) -> str | None:
    """成功返回 None，失败返回错误信息"""
    webp_path = source_path.with_suffix(".webp")
    try:
        with Image.open(source_path) as img:
            if img.mode == "P":
                img = img.convert("RGBA") if "transparency" in img.info else img.convert("RGB")
            elif img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")

            img.save(webp_path, "WEBP", quality=85, method=6)

            if replace:
                source_path.unlink()
        return None
    except Exception as e:
        return f"{source_path} -> {e}"


def convert_images_parallel(
    source_files: list[Path],
    replace: bool = False,
    *,
    make_progress: ProgressFactory | None = None,
) -> ConvertResult:
    factory = make_progress or tqdm_factory
    bar = factory(len(source_files), "Converting images")
    converted = 0
    failed = 0
    errors: list[str] = []

    with ThreadPoolExecutor() as executor:
        futures: list[Future[str | None]] = [executor.submit(convert_single, p, replace) for p in source_files]

        for future in as_completed(futures):
            error = future.result()
            if error is None:
                converted += 1
            else:
                failed += 1
                errors.append(error)
            bar.update(1)

    bar.close()
    return ConvertResult(converted=converted, failed=failed, errors=errors)


def collect_files(input_path: Path, ext: str) -> list[Path]:
    if not input_path.exists():
        raise FileNotFoundError(f"{input_path} does not exist")

    if not input_path.is_dir():
        raise NotADirectoryError(f"{input_path} is not a directory")

    return list(input_path.rglob(ext))


def convert_images(
    input_path: Path,
    replace: bool = False,
    source_format: str = "bmp",
    *,
    make_progress: ProgressFactory | None = None,
) -> Result[ConvertResult]:
    try:
        source_files = collect_files(input_path, ext=f"*.{source_format.lower()}")
    except (FileNotFoundError, NotADirectoryError) as e:
        return Result(False, str(e))
    data = convert_images_parallel(source_files, replace=replace, make_progress=make_progress)
    message = f"转换 {data.converted} 张"
    if data.failed:
        message += f"，失败 {data.failed} 张"
    return Result(True, message, data)
