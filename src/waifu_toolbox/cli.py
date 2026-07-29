import argparse
import random

from .command import (
    CacheCommand,
    ClassifyCommand,
    CommandType,
    ConvertCommand,
    RepoCommand,
    SortCommand,
)

random.seed(42)


# -----------------------------
# 主函数
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Waifu Toolbox CLI")
    subparsers = parser.add_subparsers(title="subcommands", dest="command", required=True)

    # 注册所有一级命令
    commands: list[CommandType] = [RepoCommand, CacheCommand, ClassifyCommand, SortCommand, ConvertCommand]
    command_map: dict[str, CommandType] = {}
    for cmd_cls in commands:
        sub_parser = subparsers.add_parser(cmd_cls.name, help=cmd_cls.help)
        cmd_cls.add_arguments(sub_parser)
        command_map[cmd_cls.name] = cmd_cls

    args = parser.parse_args()
    command_map[args.command].execute(args)


if __name__ == "__main__":
    main()
