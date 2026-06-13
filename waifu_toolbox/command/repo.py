import argparse
from pathlib import Path
from typing import List

from .base import Command, CommandType


# ============================
# repo 子命令集合
# ============================
class RepoCreateCommand(Command):
    name = "create"
    help = "Create a new repository from a labeled folder"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-n", "--name", required=True, help="Repository name")
        parser.add_argument("-p", "--path", type=Path, required=True, help="Path to labeled image folder")
        parser.add_argument("--ccip", action="store_true", help="Extract CCIP features")
        parser.add_argument("--dreamsim", action="store_true", help="Extract DreamSim features")

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..db.operations import create_repo

        create_repo(args.name, args.path, extract_ccip=args.ccip, extract_dreamsim=args.dreamsim)


class RepoUpdateCommand(Command):
    name = "update"
    help = "Update an existing repository"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-n", "--name", required=True, help="Repository name")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--purge", action="store_true", help="Remove images no longer on disk")
        group.add_argument("--deduplicate", action="store_true", help="Deduplicate images by hash")
        group.add_argument("--set-path", type=Path, default=None, help="Set or change repository root path")
        group.add_argument("--rename", type=str, default=None, help="Rename the repository")
        parser.add_argument("--ccip", action="store_true", help="Extract/update CCIP features")
        parser.add_argument("--dreamsim", action="store_true", help="Extract/update DreamSim features")

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..db.operations import (
            change_repo_path,
            deduplicate_repo,
            purge_repo,
            rename_repo,
            update_repo,
        )

        if args.purge:
            purge_repo(args.name)
        elif args.deduplicate:
            deduplicate_repo(args.name)
        elif args.set_path:
            change_repo_path(args.name, new_path=args.set_path)
        elif args.rename:
            rename_repo(args.name, args.rename)
        else:
            update_repo(args.name, extract_ccip=args.ccip, extract_dreamsim=args.dreamsim)


class RepoListCommand(Command):
    name = "list"
    help = "List all repositories"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        pass

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..db.operations import list_repos

        list_repos()


class RepoInfoCommand(Command):
    name = "info"
    help = "Show repository information"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-n", "--name", required=True, help="Repository name")

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..db.operations import show_repo_info

        show_repo_info(args.name)


class RepoFlattenCommand(Command):
    name = "flatten"
    help = "Flatten the repository structure"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-n", "--name", required=True, help="Repository name")

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..db.operations import flatten_repo

        flatten_repo(args.name)


class RepoAnalyzeCommand(Command):
    name = "analyze"
    help = "Analyze the repository"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-n", "--name", required=True, help="Repository name")
        parser.add_argument("-c", "--category", action="store_true", help="Analyze category distribution")
        parser.add_argument("-d", "--dir", type=str, default="", help="Analyze distribution in a specific subdirectory")
        parser.add_argument(
            "-s", "--sort", choices=["count", "size", "none"], default="none", help="Sort by count or size"
        )

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..db.analysis import analyze_repo

        analyze_repo(
            args.name,
            type="category" if args.category else "extension",
            target=args.dir,
            sort_key=args.sort,
        )


class RepoSearchCommand(Command):
    name = "search"
    help = "Search for similar images in a repository using DreamSim"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-n", "--name", required=True, help="Repository name")
        parser.add_argument("-i", "--image", type=Path, required=True, help="Query image path")
        parser.add_argument("-k", "--top-k", type=int, default=5, help="Number of results (default: 10)")
        parser.add_argument("--skip-update", action="store_true", help="Skip automatic index update before search")

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..db.operations import search_similar

        search_similar(args.name, args.image, args.top_k, skip_update=args.skip_update)


# repo 二级子命令集合
class RepoCommand(Command):
    name = "repo"
    help = "Manage feature repositories"

    subcommands: List[CommandType] = [
        RepoCreateCommand,
        RepoUpdateCommand,
        RepoListCommand,
        RepoInfoCommand,
        RepoFlattenCommand,
        RepoAnalyzeCommand,
        RepoSearchCommand,
    ]

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        subparsers = parser.add_subparsers(title="repo commands", dest="repo_command", required=True)
        for cmd_cls in RepoCommand.subcommands:
            sub_parser = subparsers.add_parser(cmd_cls.name, help=cmd_cls.help)
            cmd_cls.add_arguments(sub_parser)

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        for cmd_cls in RepoCommand.subcommands:
            if args.repo_command == cmd_cls.name:
                cmd_cls.execute(args)
                return
