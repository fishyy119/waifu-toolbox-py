from pathlib import Path

from .base import Command


# -----------------------------
# convert 命令
# -----------------------------
class ConvertCommand(Command):
    name = "convert"
    help = "Convert images between different formats"

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("input", type=Path, help="Path to the input image or directory")
        parser.add_argument("-r", "--replace", action="store_true", help="Replace original files (use with caution)")
        # parser.add_argument("-f", "--format", type=str, choices=["jpg", "png", "webp"], help="Output image format")

    @staticmethod
    def execute(args):
        from ..core.convert import convert_images

        convert_images(args.input, args.replace)
