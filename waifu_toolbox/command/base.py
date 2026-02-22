import argparse


# -----------------------------
# 命令基类
# -----------------------------
class Command:
    name: str = ""
    help: str = ""

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        """子类实现：在 parser 上添加参数"""
        pass

    @staticmethod
    def execute(args: argparse.Namespace):
        """子类实现：执行逻辑"""
        pass
