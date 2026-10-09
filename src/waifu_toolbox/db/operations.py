from typing import Any

from sqlalchemy import Row, delete, distinct, func, select, update
from sqlalchemy.sql import Select

from . import connection as db_module
from .models import CacheClearResult, ImageInfo, RepoImages, RepoInfo, RepoSummary
from .repo import RepoStorage
from .schema import feature_cache, images, repos


def get_repo_images(repo_name: str) -> RepoImages | None:
    """返回仓库图片列表，仓库不存在时返回 None"""
    db = RepoStorage()
    if not db.load(repo_name):
        return None
    assert db.repo_path is not None
    images = [ImageInfo(relative_path=rp, label=lb) for rp, lb in zip(db.relative_paths, db.labels, strict=False)]
    return RepoImages(repo_path=db.repo_path, images=images)


def list_repos() -> list[RepoSummary]:
    with db_module.database.connect() as conn:
        rows = conn.execute(select(repos.c.name, repos.c.path).order_by(repos.c.name)).all()
        return [RepoSummary(name=name, path=path) for name, path in rows]


def _repo_infos_query(repo_name: str | None = None) -> Select[Any, Any, int, int, int, int]:
    statement = (
        select(
            repos.c.name,
            repos.c.path,
            func.count(images.c.hash),
            func.count(distinct(images.c.label)),
            func.count(images.c.ccip_feature),
            func.count(images.c.dreamsim_feature),
        )
        .select_from(repos.outerjoin(images, images.c.repo_id == repos.c.repo_id))
        .group_by(repos.c.repo_id, repos.c.name, repos.c.path)
        .order_by(repos.c.name)
    )
    if repo_name is not None:
        statement = statement.where(repos.c.name == repo_name)
    return statement


def _row_to_repo_info(row: Row[Any, Any, int, int, int, int]) -> RepoInfo:
    return RepoInfo(
        name=row[0],
        path=row[1],
        total_images=row[2],
        label_count=row[3],
        ccip_count=row[4],
        dreamsim_count=row[5],
    )


def list_repo_infos() -> list[RepoInfo]:
    with db_module.database.connect() as conn:
        rows = conn.execute(_repo_infos_query()).all()
        return [_row_to_repo_info(row) for row in rows]


def get_repo_info(repo_name: str) -> RepoInfo | None:
    with db_module.database.connect() as conn:
        row = conn.execute(_repo_infos_query(repo_name)).one_or_none()
        if row is None:
            return None
        return _row_to_repo_info(row)


def repo_exists(repo_name: str) -> bool:
    with db_module.database.connect() as conn:
        return conn.execute(select(repos.c.repo_id).where(repos.c.name == repo_name)).first() is not None


def rename_repo(repo_name: str, new_name: str) -> bool:
    with db_module.database.begin() as conn:
        result = conn.execute(update(repos).where(repos.c.name == repo_name).values(name=new_name))
        return result.rowcount > 0


def delete_repo(repo_name: str) -> bool:
    with db_module.database.begin() as conn:
        result = conn.execute(delete(repos).where(repos.c.name == repo_name))
        return result.rowcount > 0


def change_repo_path(repo_name: str, new_path: str) -> bool:
    with db_module.database.begin() as conn:
        result = conn.execute(update(repos).where(repos.c.name == repo_name).values(path=new_path))
        return result.rowcount > 0


def clear_cache(ccip: bool, dreamsim: bool) -> CacheClearResult:
    with db_module.database.begin() as conn:
        ccip_count = 0
        dreamsim_count = 0

        if ccip:
            ccip_count = conn.execute(
                select(func.count()).select_from(feature_cache).where(feature_cache.c.feature_type == "ccip")
            ).scalar_one()
            conn.execute(delete(feature_cache).where(feature_cache.c.feature_type == "ccip"))

        if dreamsim:
            dreamsim_count = conn.execute(
                select(func.count()).select_from(feature_cache).where(feature_cache.c.feature_type == "dreamsim")
            ).scalar_one()
            conn.execute(delete(feature_cache).where(feature_cache.c.feature_type == "dreamsim"))

        data = CacheClearResult(ccip_deleted=ccip_count, dreamsim_deleted=dreamsim_count)
        return data
