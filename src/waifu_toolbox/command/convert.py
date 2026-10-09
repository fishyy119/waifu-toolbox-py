from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..utils.console import log_error, log_info
from .base import Command

if TYPE_CHECKING:
    import argparse


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
        message = f"转换 {result.converted} 张"
        if result.failed:
            message += f"，失败 {result.failed} 张"
        log_info(message)
        for error in result.errors:
            log_error(error)
