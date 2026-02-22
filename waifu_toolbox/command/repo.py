from pathlib import Path

from .base import Command


# ============================
# repo 子命令集合
# ============================
class RepoCreateCommand(Command):
    name = "create"
    help = "Create a new repository from a labeled folder"

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("-n", "--name", required=True, help="Repository name")
        parser.add_argument("-p", "--path", type=Path, required=True, help="Path to labeled image folder")

    @staticmethod
    def execute(args):
        from ..db.operations import create_repo

        create_repo(args.name, args.path)


class RepoUpdateCommand(Command):
    name = "update"
    help = "Update an existing repository"

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("-n", "--name", required=True, help="Repository name")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--purge", action="store_true", help="Remove images no longer on disk")
        group.add_argument("--deduplicate", action="store_true", help="Deduplicate images by hash")
        group.add_argument("--set-path", type=Path, default=None, help="Set or change repository root path")

    @staticmethod
    def execute(args):
        from ..db.operations import (
            change_repo_path,
            deduplicate_repo,
            purge_repo,
            update_repo,
        )

        if args.purge:
            purge_repo(args.name)
        elif args.deduplicate:
            deduplicate_repo(args.name)
        elif args.set_path:
            change_repo_path(args.name, new_path=args.set_path)
        else:
            update_repo(args.name)


class RepoInfoCommand(Command):
    name = "info"
    help = "Show repository information"

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("-n", "--name", required=True, help="Repository name")

    @staticmethod
    def execute(args):
        from ..db.operations import show_repo_info

        show_repo_info(args.name)


class RepoFlattenCommand(Command):
    name = "flatten"
    help = "Flatten the repository structure"

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("-n", "--name", required=True, help="Repository name")

    @staticmethod
    def execute(args):
        from ..db.operations import flatten_repo

        flatten_repo(args.name)


class RepoAnalyzeCommand(Command):
    name = "analyze"
    help = "Analyze the repository"

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("-n", "--name", required=True, help="Repository name")
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument("-c", "--category", action="store_true", help="Analyze category distribution")
        group.add_argument("-d", "--dir", type=str, help="Analyze distribution in a specific subdirectory")

    @staticmethod
    def execute(args):
        from ..db.analysis import analyze_repo

        if args.category:
            analyze_repo(args.name, type="_category")
        elif args.dir:
            analyze_repo(args.name, type=args.dir)
        else:
            analyze_repo(args.name)


# repo 二级子命令集合
class RepoCommand(Command):
    name = "repo"
    help = "Manage feature repositories"

    subcommands = [
        RepoCreateCommand,
        RepoUpdateCommand,
        RepoInfoCommand,
        RepoFlattenCommand,
        RepoAnalyzeCommand,
    ]

    @staticmethod
    def add_arguments(parser):
        subparsers = parser.add_subparsers(title="repo commands", dest="repo_command", required=True)
        for cmd_cls in RepoCommand.subcommands:
            sub_parser = subparsers.add_parser(cmd_cls.name, help=cmd_cls.help)
            cmd_cls.add_arguments(sub_parser)

    @staticmethod
    def execute(args):
        for cmd_cls in RepoCommand.subcommands:
            if args.repo_command == cmd_cls.name:
                cmd_cls.execute(args)
                return
