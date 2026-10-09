from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from rich import box, print
from rich.console import Console
from rich.table import Table

from ..utils.console import log_error, log_info
from .base import Command, CommandType

if TYPE_CHECKING:
    import argparse

    from ..core.analysis import FileStat


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
        from ..core.operations import create_repo

        result = create_repo(args.name, args.path, extract_ccip=args.ccip, extract_dreamsim=args.dreamsim)
        message = f"仓库 '{args.name}' 创建成功"
        if result.label_mismatches:
            message += "\n\n标签冲突（同 hash 不同标签，仅保留首次出现）:\n"
            message += "\n".join(f"  {m}" for m in result.label_mismatches)
        log_info(message)


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
        from ..core.operations import (
            change_repo_path,
            deduplicate_repo,
            purge_repo,
            rename_repo,
            update_repo,
        )

        if args.purge:
            removed = purge_repo(args.name)
            log_info(f"清除了 {removed} 条失效记录" if removed > 0 else "没有需要清除的记录")
        elif args.deduplicate:
            deduplicated = deduplicate_repo(args.name)
            parts: list[str] = []
            if deduplicated.deleted > 0:
                parts.append(f"删除了 {deduplicated.deleted} 张重复图片")
            if deduplicated.label_mismatches:
                parts.append(f"{len(deduplicated.label_mismatches)} 条标签不一致")
            log_info("、".join(parts) if parts else "未发现重复")
            for mismatch in deduplicated.label_mismatches:
                log_error(f"标签不一致: {mismatch}")
        elif args.set_path:
            change_repo_path(args.name, new_path=args.set_path)
            log_info("路径已更新")
        elif args.rename:
            rename_repo(args.name, args.rename)
            log_info(f"已重命名为 '{args.rename}'")
        else:
            updated = update_repo(args.name, extract_ccip=args.ccip, extract_dreamsim=args.dreamsim)
            log_info(
                f"新增 {updated.new_images} 张图片，更新 {updated.updated_labels} 个标签"
                if updated.new_images or updated.updated_labels
                else "仓库已是最新"
            )


class RepoRemoveCommand(Command):
    name = "rm"
    help = "Remove a repository index without deleting files on disk"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-n", "--name", required=True, help="Repository name")

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..core.operations import delete_repo

        delete_repo(args.name)
        log_info(f"已删除仓库 '{args.name}' 的索引（未删除磁盘文件）")


class RepoListCommand(Command):
    name = "list"
    help = "List all repositories"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        pass

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..core.operations import list_repos

        rows = list_repos()
        if not rows:
            log_info("暂无仓库")
            return
        table = Table(show_header=True, header_style="bold")
        table.add_column("Name", style="magenta bold")
        table.add_column("Path", style="orchid")
        for r in rows:
            table.add_row(r.name, r.path)
        print(table)


class RepoInfoCommand(Command):
    name = "info"
    help = "Show repository information"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-n", "--name", required=True, help="Repository name")

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..core.operations import get_repo_info

        info = get_repo_info(args.name)
        if info is None:
            log_error(f"仓库 '{args.name}' 不存在")
            return

        def _fmt(count: int, total: int) -> str:
            if count == total:
                return f"[green]{count}/{total}[/green]"
            elif count > 0:
                return f"[yellow]{count}/{total}[/yellow]"
            return f"[red]{count}/{total}[/red]"

        table = Table(show_header=False, title=info.name, title_style="magenta bold")
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_row("Path", f"[orchid]{info.path}[/orchid]")
        table.add_row("Images", str(info.total_images))
        table.add_row("Labels", str(info.label_count))
        table.add_row("CCIP features", _fmt(info.ccip_count, info.total_images))
        table.add_row("DreamSim features", _fmt(info.dreamsim_count, info.total_images))
        print(table)


class RepoFlattenCommand(Command):
    name = "flatten"
    help = "Flatten the repository structure"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-n", "--name", required=True, help="Repository name")

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..core.operations import flatten_repo

        result = flatten_repo(args.name)
        log_info(f"输出文件夹: {result}")


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
        from ..core.analysis import analyze_repo

        analysis_type = "category" if args.category else "extension"
        result = analyze_repo(args.name, type=analysis_type, target=args.dir)
        title = f"{analysis_type.capitalize()} Analysis: {args.name}" + (f"/{args.dir}" if args.dir else "")
        _print_stats(result, title=title, sort_key=args.sort)


def _print_stats(
    stats: dict[str, FileStat],
    title: str = "Statistics",
    sort_key: str = "none",
) -> None:
    total_count = sum(stat.count for stat in stats.values())
    total_size = sum(stat.size for stat in stats.values())

    sorted_keys: list[tuple[str, float]] = []
    for key, stat in stats.items():
        size_mb = stat.size / (1024 * 1024)
        sort_value = {"count": float(stat.count), "size": size_mb, "none": 0.0}[sort_key]
        sorted_keys.append((key, sort_value))

    console = Console()
    table = Table(title=title, box=box.SIMPLE_HEAVY, show_lines=False, show_footer=True)
    table.add_column("Type", justify="left", footer="Total", style="bold")
    table.add_column("Count", justify="right", footer=f"{total_count}")
    table.add_column("Count %", justify="right", footer="100.00%" if total_count else "0.00%")
    table.add_column("Size (MB)", justify="right", footer=f"{total_size / (1024 * 1024):.2f}")
    table.add_column("Size %", justify="right", footer="100.00%" if total_size else "0.00%")

    sorted_keys.sort(key=lambda r: r[1], reverse=True)
    for key, _ in sorted_keys:
        stat = stats[key]
        size_mb = stat.size / (1024 * 1024)
        count_ratio = stat.count / total_count if total_count else 0
        size_ratio = stat.size / total_size if total_size else 0
        table.add_row(key, f"{stat.count}", f"{count_ratio:.2%}", f"{size_mb:.2f}", f"{size_ratio:.2%}")

    console.print(table)


class RepoSearchCommand(Command):
    name = "search"
    help = "Search for similar images in a repository using DreamSim"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-n", "--name", required=True, help="Repository name")
        parser.add_argument("-i", "--image", type=Path, required=True, help="Query image path")
        parser.add_argument("-k", "--top-k", type=int, default=5, help="Number of results (default: 10)")
        parser.add_argument("--update", action="store_true", help="Update index before search")

    @staticmethod
    def execute(args: argparse.Namespace) -> None:
        from ..core.operations import search_similar

        results = search_similar(args.name, args.image, args.top_k, skip_update=not args.update)

        table = Table(show_header=True, header_style="bold", title=f"Top {len(results)} similar images")
        table.add_column("#", style="dim", width=4)
        table.add_column("Path", style="orchid")
        table.add_column("Label", style="magenta bold")
        table.add_column("Similarity", style="green", justify="right")
        for r in results:
            table.add_row(str(r.rank), r.path, r.label, f"{r.similarity:.4f}")
        print(table)


# repo 二级子命令集合
class RepoCommand(Command):
    name = "repo"
    help = "Manage feature repositories"

    subcommands: ClassVar[list[CommandType]] = [
        RepoCreateCommand,
        RepoUpdateCommand,
        RepoRemoveCommand,
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
