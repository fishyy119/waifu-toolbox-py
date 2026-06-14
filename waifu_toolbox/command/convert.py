import argparse
from pathlib import Path

from ..utils.console import log_error, log_info
from .base import Command


# -----------------------------
# convert 命令
# -----------------------------
class ConvertCommand(Command):
    name = "convert"
    help = "Convert images between different formats"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        parser.add_argument("input", type=Path, help="Path to the input image or directory")
        parser.add_argument("-r", "--replace", action="store_true", help="Replace original files (use with caution)")
        parser.add_argument(
            "-f",
            "--format",
            type=str,
            choices=["jpg", "png", "jpeg", "bmp"],
            help="Format wait for convert",
            default="bmp",
        )

    @staticmethod
    def execute(args: argparse.Namespace):
        from ..core.convert import convert_images

        result = convert_images(args.input, args.replace, source_format=args.format)
        if result.ok:
            log_info(result.message)
            if result.data:
                for error in result.data.errors:
                    log_error(error)
        else:
            log_error(result.message)
