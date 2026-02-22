from pathlib import Path

from .base import Command


# -----------------------------
# sort 命令
# -----------------------------
class SortCommand(Command):
    name = "sort"
    help = "Sort images in directories based on perceptual similarity (LPIPS + UMAP)"

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("dir", type=Path, help="Root directory containing images or subdirectories to sort")
        parser.add_argument("-m", "--memory-limit", type=int, default=2048, help="Memory limit in MB")
        parser.add_argument("--avoid-sorted", action="store_true", help="Avoid sorting already sorted directories")

    @staticmethod
    def execute(args):
        from ..core.sort import sort_images_by_perceptual_similarity

        sort_images_by_perceptual_similarity(args.dir, args.memory_limit, args.avoid_sorted)
