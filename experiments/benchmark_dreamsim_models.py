import argparse
import json
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

import numpy as np
from PIL import Image
from rich.console import Console
from rich.table import Table
from tqdm import tqdm

from waifu_toolbox.paths import PATHS
from waifu_toolbox.utils.dreamsim import DREAMSIM_DEVICE, compute_dreamsim_distance_matrix
from waifu_toolbox.utils.image import IMG_EXTS

DreamSimModelName = Literal[
    "ensemble",
    "dino_vitb16",
    "clip_vitb32",
    "open_clip_vitb32",
    "dinov2_vitb14",
    "synclr_vitb16",
]

DEFAULT_MODELS: list[DreamSimModelName] = [
    "ensemble",  # 2.3GB
    # "dino_vitb16",
    # "clip_vitb32",
    # "open_clip_vitb32",
    # "dinov2_vitb14",
    "synclr_vitb16",  # 636MB
]


@dataclass(slots=True)
class BenchmarkResult:
    model: str
    image_count: int
    embedding_dim: int
    load_seconds: float
    warmup_seconds: float
    embedding_seconds: float
    distance_seconds: float
    total_seconds: float
    milliseconds_per_image: float
    images_per_second: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark DreamSim model throughput on the highest-resolution images in a directory.",
    )
    parser.add_argument("images_root", type=Path, help="Directory containing benchmark images")
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="DreamSim model names to benchmark",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of images to benchmark",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=5,
        help="Number of warmup images per model",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON file path for benchmark results",
    )
    return parser.parse_args()


def collect_benchmark_images(root: Path, count: int) -> list[Path]:
    if not root.exists():
        raise FileNotFoundError(root)

    candidates: list[Path] = []
    for ext in IMG_EXTS:
        candidates.extend(root.rglob(ext))
    candidates.sort()

    image_infos: list[tuple[int, Path]] = []
    for path in tqdm(candidates, desc="筛选基准图片", unit="img"):
        try:
            with Image.open(path) as img:
                width, height = img.size
                image_infos.append((width * height, path))
        except OSError:
            continue

    if len(image_infos) < count:
        raise RuntimeError(
            f"仅找到 {len(image_infos)} 张可读取图片，无法满足 {count} 张基准测试需求。"
        )

    image_infos.sort(key=lambda item: (-item[0], str(item[1])))
    return [path for _, path in image_infos[:count]]


def load_input_tensor(image_path: Path, preprocess):
    with Image.open(image_path) as img:
        return preprocess(img).to(DREAMSIM_DEVICE)


def benchmark_model(
    model_name: DreamSimModelName,
    image_paths: Sequence[Path],
    warmup: int,
) -> BenchmarkResult:
    import torch
    from dreamsim import dreamsim

    cache_dir = PATHS.dreamsim_model_root / model_name
    cache_dir.mkdir(parents=True, exist_ok=True)

    load_start = time.perf_counter()
    model, preprocess = dreamsim(
        pretrained=True,
        device=DREAMSIM_DEVICE,
        cache_dir=str(cache_dir),
        dreamsim_type=model_name,
    )
    load_seconds = time.perf_counter() - load_start

    warmup_paths = list(image_paths[: min(warmup, len(image_paths))])
    warmup_start = time.perf_counter()
    with torch.inference_mode():
        for image_path in warmup_paths:
            input_tensor = load_input_tensor(image_path, preprocess)
            model.embed(input_tensor)
    warmup_seconds = time.perf_counter() - warmup_start

    embeddings: list[np.ndarray] = []
    embedding_start = time.perf_counter()
    with torch.inference_mode():
        for image_path in tqdm(image_paths, desc=f"{model_name} embedding", unit="img", leave=False):
            input_tensor = load_input_tensor(image_path, preprocess)
            embedding = model.embed(input_tensor)
            embeddings.append(np.asarray(embedding.detach().cpu().numpy(), dtype=np.float32).reshape(-1))
    embedding_seconds = time.perf_counter() - embedding_start

    distance_start = time.perf_counter()
    embedding_matrix = np.stack(embeddings, axis=0)
    compute_dreamsim_distance_matrix(embedding_matrix)
    distance_seconds = time.perf_counter() - distance_start

    total_seconds = load_seconds + warmup_seconds + embedding_seconds + distance_seconds
    return BenchmarkResult(
        model=model_name,
        image_count=len(image_paths),
        embedding_dim=embedding_matrix.shape[1],
        load_seconds=load_seconds,
        warmup_seconds=warmup_seconds,
        embedding_seconds=embedding_seconds,
        distance_seconds=distance_seconds,
        total_seconds=total_seconds,
        milliseconds_per_image=embedding_seconds * 1000 / len(image_paths),
        images_per_second=len(image_paths) / embedding_seconds,
    )


def print_results(results: Sequence[BenchmarkResult]) -> None:
    console = Console()
    table = Table(title="DreamSim 模型效率对比")
    table.add_column("Model", justify="left")
    table.add_column("Count", justify="right")
    table.add_column("Dim", justify="right")
    table.add_column("Load(s)", justify="right")
    table.add_column("Warmup(s)", justify="right")
    table.add_column("Embed(s)", justify="right")
    table.add_column("Dist(s)", justify="right")
    table.add_column("Total(s)", justify="right")
    table.add_column("ms/img", justify="right")
    table.add_column("img/s", justify="right")

    for result in results:
        table.add_row(
            result.model,
            str(result.image_count),
            str(result.embedding_dim),
            f"{result.load_seconds:.3f}",
            f"{result.warmup_seconds:.3f}",
            f"{result.embedding_seconds:.3f}",
            f"{result.distance_seconds:.3f}",
            f"{result.total_seconds:.3f}",
            f"{result.milliseconds_per_image:.2f}",
            f"{result.images_per_second:.2f}",
        )

    console.print(table)


def save_results(results: Sequence[BenchmarkResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    image_paths = collect_benchmark_images(args.images_root, args.count)

    results: list[BenchmarkResult] = []
    for model_name in cast("Sequence[DreamSimModelName]", args.models):
        results.append(
            benchmark_model(
                model_name=model_name,
                image_paths=image_paths,
                warmup=args.warmup,
            )
        )

    print_results(results)

    if args.output is not None:
        save_results(results, args.output)


if __name__ == "__main__":
    main()
