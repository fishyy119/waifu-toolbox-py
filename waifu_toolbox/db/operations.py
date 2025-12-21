import shutil
from pathlib import Path

from tqdm import tqdm

from ..utils.console import log_error, log_info
from .ccip_db import ImageDBCCIP


def create_repo(repo_name: str, path: Path) -> None:
    db = ImageDBCCIP()
    if db.scan_init(repo_name, path):
        db.save()


def change_repo_path(repo_name: str, new_path: Path) -> None:
    db = ImageDBCCIP(repo_name)
    db.repo_path = new_path
    db.save()


def deduplicate_repo(repo_name: str) -> None:
    db = ImageDBCCIP()
    db.deduplicate(repo_name)


def update_repo(repo_name: str) -> None:
    db = ImageDBCCIP()
    if db.update(repo_name):
        db.save()


def purge_repo(repo_name: str) -> None:
    db = ImageDBCCIP()
    if db.purge(repo_name):
        db.save()


def show_repo_info(repo_name: str) -> None:
    db = ImageDBCCIP()
    db.load(repo_name)
    print(f"Repository:           {repo_name}")
    print(f"Number of images:     {db.size}")
    print(f"Repository path:      {db.repo_path}")

    assert db.db_path is not None, "repo_path 未设置"
    print("-------------------------------------")
    print(f"index.npz:            {(db.db_path / 'index.npz').stat().st_size / (1024 * 1024):.2f} MB")
    print(f"meta.pkl:             {(db.db_path / 'meta.pkl').stat().st_size / (1024 * 1024):.2f} MB")


def flatten_repo(repo_name: str) -> None:
    # 虽然归属到 repo 命令下，但它只利用里面存储的仓库路径信息，不涉及数据库操作
    db = ImageDBCCIP()
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
                    log_error(f"发现重复的文件名: {target_file.name}，请先手动处理后再进行扁平化操作")
                    exit(1)

                shutil.copy2(file, target_file)

    log_info(f"输出文件夹已创建: {flat_dir}")
