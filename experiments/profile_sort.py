import datetime
import sys
from pathlib import Path

from line_profiler import LineProfiler

from waifu_toolbox.core import sort as sort_module


def main(images_root: Path):
    sort_module.sort_images_by_perceptual_similarity(images_root, False)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python profile_sort.py <images_root>")
        sys.exit(1)

    images_root = Path(sys.argv[1])
    if not images_root.exists():
        raise FileNotFoundError(images_root)

    profiler = LineProfiler()
    profiler.add_module(sort_module)
    profiler(main)(images_root)

    profile_filename = f"profile_sort_{datetime.datetime.now().strftime('%H%M%S')}.txt"
    with open(profile_filename, "w", encoding="utf-8") as f:
        profiler.print_stats(sort=True, stream=f)
