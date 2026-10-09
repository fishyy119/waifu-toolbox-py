from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.engine import Connection

from tests.helpers import FakeProgressReporter
from waifu_toolbox.db import connection as db_module
from waifu_toolbox.db.connection import Database
from waifu_toolbox.paths import AppPaths
from waifu_toolbox.utils.progress import ProgressFactory

# 模块导入不再迁移数据库；每个测试通过 fixture 替换全局管理器。


@pytest.fixture
def app_paths(tmp_path: Path) -> AppPaths:
    return AppPaths(
        waifu_home=tmp_path / ".waifu",
        database_root=tmp_path / ".waifu" / "database",
        waifu_db=tmp_path / ".waifu" / "database" / "waifu.db",
        dreamsim_model_root=tmp_path / ".waifu" / "dreamsim_models",
    )


@pytest.fixture
def isolated_db(app_paths: AppPaths) -> Path:
    return app_paths.waifu_db


@pytest.fixture
def database(isolated_db: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Database]:
    # 每个测试独立管理初始化状态，并在结束时释放 SQLite 文件句柄。
    database = Database(isolated_db)
    monkeypatch.setattr(db_module, "database", database)
    try:
        yield database
    finally:
        database.close()


@pytest.fixture
def db_conn(database: Database) -> Iterator[Connection]:
    with database.begin() as conn:
        yield conn


@pytest.fixture
def make_progress() -> ProgressFactory:
    def factory(total: int, desc: str) -> FakeProgressReporter:
        return FakeProgressReporter(total=total, desc=desc)

    return factory
