import argparse
from pathlib import Path

from ..utils.console import log_error, log_info
from .base import Command


# -----------------------------
# sort 命令
# -----------------------------
class SortCommand(Command):
    name = "sort"
    help = "Sort images in directories based on DreamSim similarity (DreamSim + UMAP)"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("dir", type=Path, help="Root directory containing images or subdirectories to sort")
        parser.add_argument("--avoid-sorted", action="store_true", help="Avoid sorting already sorted directories")

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..core.sort import sort_images_by_perceptual_similarity

        result = sort_images_by_perceptual_similarity(args.dir, args.avoid_sorted)
        if result.ok:
            log_info(result.message)
        else:
            log_error(result.message)
