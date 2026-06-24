import argparse
from pathlib import Path

from ..utils.console import log_error, log_info
from .base import Command


# -----------------------------
# classify 命令
# -----------------------------
class ClassifyCommand(Command):
    name = "classify"
    help = "Classify images based on labeled repository and CCIP clustering"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        parser.add_argument("wait_classify", type=Path, help="Path to root folder of images to classify")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-r", "--repo", type=str, default=None, help="Name of the labeled repository")
        group.add_argument("--inplace", action="store_true", help="If just cluster, save report in original folder")
        parser.add_argument(
            "-n", "--num-references", type=int, default=20, help="Number of reference images per category"
        )

    @staticmethod
    def execute(args: argparse.Namespace):
        if args.repo is None:
            from ..core.classification import just_cluster_by_ccip

            result = just_cluster_by_ccip(args.wait_classify, args.inplace)
        else:
            from ..core.classification import classify_by_ccip

            result = classify_by_ccip(args.repo, args.wait_classify, args.num_references)
        if result.ok:
            log_info(result.message)
        else:
            log_error(result.message)
