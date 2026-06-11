import shutil
from pathlib import Path

from rich import print
from rich.table import Table
from tqdm import tqdm

from ..utils.console import log_error, log_info
from .connection import get_connection
from .repo import ImageRepo


def create_repo(repo_name: str, path: Path, extract_ccip: bool = False, extract_dreamsim: bool = False) -> None:
    conn = get_connection()
    if conn.execute("""SELECT 1 FROM repos WHERE name = ?""", (repo_name,)).fetchone():
        log_error(f"仓库 '{repo_name}' 已存在，请使用其他名称或先删除已有仓库")
        return

    db = ImageRepo()
    if db.scan_init(repo_name, path, extract_ccip=extract_ccip, extract_dreamsim=extract_dreamsim):
        db.save()


def rename_repo(repo_name: str, new_name: str) -> None:
    conn = get_connection()
    if conn.execute("""SELECT 1 FROM repos WHERE name = ?""", (new_name,)).fetchone():
        log_error(f"仓库 '{new_name}' 已存在")
        return
    with conn:
        result = conn.execute(
            """UPDATE repos SET name = ? WHERE name = ?""",
            (new_name, repo_name),
        )
        if result.rowcount == 0:
            log_error(f"仓库 '{repo_name}' 不存在")
            return
    log_info(f"已将仓库 [magenta bold]{repo_name}[/magenta bold] 重命名为 [magenta bold]{new_name}[/magenta bold]")


def list_repos() -> None:
    conn = get_connection()
    rows = conn.execute("""SELECT name, path FROM repos ORDER BY name""").fetchall()
    if not rows:
        log_info("暂无仓库")
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="magenta bold")
    table.add_column("Path", style="orchid")
    for name, path in rows:
        table.add_row(name, path)
    print(table)


def change_repo_path(repo_name: str, new_path: Path) -> None:
    conn = get_connection()
    with conn:
        result = conn.execute(
            """UPDATE repos SET path = ? WHERE name = ?""",
            (str(new_path), repo_name),
        )
        if result.rowcount == 0:
            log_error(f"仓库 '{repo_name}' 不存在")
            return
    log_info(f"已将仓库 '{repo_name}' 的路径更新为 [orchid]{new_path}[/orchid]")


def deduplicate_repo(repo_name: str) -> None:
    db = ImageRepo()
    db.deduplicate(repo_name)


def update_repo(repo_name: str, extract_ccip: bool = False, extract_dreamsim: bool = False) -> None:
    db = ImageRepo()
    db.update(repo_name, extract_ccip=extract_ccip, extract_dreamsim=extract_dreamsim)


def purge_repo(repo_name: str) -> None:
    db = ImageRepo()
    db.purge(repo_name)


def show_repo_info(repo_name: str) -> None:
    db = ImageRepo()
    if db.load(repo_name):
        label_counts: dict[str, int] = {}
        for label in db.labels:
            label_counts[label] = label_counts.get(label, 0) + 1

        total, ccip_count, ds_count = db.feature_status()

        def _fmt_coverage(count: int, total: int) -> str:
            if count == total:
                return f"[green]{count}/{total}[/green]"
            elif count > 0:
                return f"[yellow]{count}/{total}[/yellow]"
            else:
                return f"[red]{count}/{total}[/red]"

        table = Table(show_header=False, title=repo_name, title_style="magenta bold")
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_row("Path", f"[orchid]{db.repo_path}[/orchid]")
        table.add_row("Images", str(total))
        table.add_row("Labels", str(len(label_counts)))
        table.add_row("CCIP features", _fmt_coverage(ccip_count, total))
        table.add_row("DreamSim features", _fmt_coverage(ds_count, total))
        print(table)


def clear_cache(ccip: bool = False, dreamsim: bool = False) -> None:
    """清空特征缓存；两个 flag 均不传时清空全部"""
    conn = get_connection()

    if not ccip and not dreamsim:
        # 全清
        count = conn.execute("""SELECT COUNT(*) FROM feature_cache""").fetchone()[0]
        with conn:
            conn.execute("""DELETE FROM feature_cache""")
        log_info(f"已清空全部特征缓存（{count} 条）。")
        return

    if ccip:
        count = conn.execute(
            """SELECT COUNT(*) FROM feature_cache WHERE feature_type = ?""",
            ("ccip",),
        ).fetchone()[0]
        with conn:
            conn.execute(
                """DELETE FROM feature_cache WHERE feature_type = ?""",
                ("ccip",),
            )
        log_info(f"已清空 CCIP 特征缓存（{count} 条）。")

    if dreamsim:
        count = conn.execute(
            """SELECT COUNT(*) FROM feature_cache WHERE feature_type = ?""",
            ("dreamsim",),
        ).fetchone()[0]
        with conn:
            conn.execute(
                """DELETE FROM feature_cache WHERE feature_type = ?""",
                ("dreamsim",),
            )
        log_info(f"已清空 DreamSim 特征缓存（{count} 条）。")


def flatten_repo(repo_name: str) -> None:
    # 虽然归属到 repo 命令下，但它只利用里面存储的仓库路径信息，不涉及数据库操作
    db = ImageRepo()
    db.load(repo_name)
    repo_root = db.repo_path
    assert repo_root is not None

    if not repo_root.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_root}")

    flat_dir = repo_root.parent / f"_{repo_name}_flat"
    if flat_dir.exists():
        shutil.rmtree(flat_dir)
    flat_dir.mkdir(exist_ok=True)

    sub_folders = [d for d in repo_root.iterdir() if d.is_dir()]  # 忽略根目录下的文件直接

    for item in tqdm(sub_folders, desc="扁平化文件夹", unit="folder"):
        for file in item.rglob("*"):
            if file.is_file():
                # 构建目标路径：只保留一级子目录
                rel_path = file.relative_to(repo_root)
                # rel_path.parts[0] 是一级目录名
                target_dir = flat_dir / rel_path.parts[0]
                target_dir.mkdir(exist_ok=True)

                target_file = target_dir / file.name
                if target_file.exists():
                    log_error(f"发现重复的文件名: [red]{target_file.name}[/red]，请先手动处理后再进行扁平化操作")
                    exit(1)

                shutil.copy2(file, target_file)

    log_info(f"输出文件夹已创建: [orchid]{flat_dir}[/orchid]")
