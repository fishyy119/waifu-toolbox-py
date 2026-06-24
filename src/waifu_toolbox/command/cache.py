import argparse
from typing import List

from ..utils.console import log_error, log_info
from .base import Command, CommandType


class CacheClearCommand(Command):
    name = "clear"
    help = "Clear the feature cache"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--ccip", action="store_true", help="Clear CCIP feature cache only")
        parser.add_argument("--dreamsim", action="store_true", help="Clear DreamSim feature cache only")

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..db.operations import clear_cache

        result = clear_cache(ccip=args.ccip, dreamsim=args.dreamsim)
        if result.ok:
            log_info(result.message)
        else:
            log_error(result.message)


# cache 二级子命令集合
class CacheCommand(Command):
    name = "cache"
    help = "Manage feature cache"

    subcommands: List[CommandType] = [CacheClearCommand]

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
