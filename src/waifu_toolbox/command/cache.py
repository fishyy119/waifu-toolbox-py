from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from ..utils.console import log_info
from .base import Command, CommandType

if TYPE_CHECKING:
    import argparse


class CacheClearCommand(Command):
    name = "clear"
    help = "Clear the feature cache"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--ccip", action="store_true", help="Clear CCIP feature cache only")
        parser.add_argument("--dreamsim", action="store_true", help="Clear DreamSim feature cache only")

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..core.operations import clear_cache

        data = clear_cache(ccip=args.ccip, dreamsim=args.dreamsim)
        clear_all = not args.ccip and not args.dreamsim
        parts: list[str] = []
        if clear_all or args.ccip:
            parts.append(f"CCIP {data.ccip_deleted} 条")
        if clear_all or args.dreamsim:
            parts.append(f"DreamSim {data.dreamsim_deleted} 条")
        log_info(f"已清空缓存（{'、'.join(parts)}，共 {data.ccip_deleted + data.dreamsim_deleted} 条）")


# cache 二级子命令集合
class CacheCommand(Command):
    name = "cache"
    help = "Manage feature cache"

    subcommands: ClassVar[list[CommandType]] = [CacheClearCommand]

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        subparsers = parser.add_subparsers(title="cache commands", dest="cache_command", required=True)
        for cmd_cls in CacheCommand.subcommands:
            sub_parser = subparsers.add_parser(cmd_cls.name, help=cmd_cls.help)
            cmd_cls.add_arguments(sub_parser)

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        for cmd_cls in CacheCommand.subcommands:
            if args.cache_command == cmd_cls.name:
                cmd_cls.execute(args)
                return
