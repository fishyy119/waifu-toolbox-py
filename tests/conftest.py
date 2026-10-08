from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy.engine import Connection

from tests.helpers import FakeProgressReporter
from waifu_toolbox import paths
from waifu_toolbox.paths import AppPaths
from waifu_toolbox.utils.progress import ProgressFactory

# 在导入默认实例前使用临时路径，避免测试收集阶段迁移真实数据库。
_test_temp_root = Path(__file__).resolve().parents[1] / ".codex-pytest-tmp"
_test_temp_root.mkdir(exist_ok=True)
with TemporaryDirectory(prefix="waifu-test-default-", dir=_test_temp_root) as default_home:
    temporary_home = Path(default_home)
    default_paths = AppPaths(
        waifu_home=temporary_home,
        database_root=temporary_home / "database",
        waifu_db=temporary_home / "database" / "waifu.db",
        dreamsim_model_root=temporary_home / "dreamsim_models",
    )
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(paths, "PATHS", default_paths)
        from waifu_toolbox.db import connection
        from waifu_toolbox.db.connection import Database

        connection.database.close()


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
    monkeypatch.setattr(connection, "database", database)
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
