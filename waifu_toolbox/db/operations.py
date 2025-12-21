from pathlib import Path

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
