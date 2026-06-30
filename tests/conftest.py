from contextlib import closing
from pathlib import Path

import pytest

from tests.helpers import FakeProgressReporter
from waifu_toolbox.db import connection
from waifu_toolbox.paths import AppPaths


@pytest.fixture
def app_paths(tmp_path: Path) -> AppPaths:
    return AppPaths(
        waifu_home=tmp_path / ".waifu",
        database_root=tmp_path / ".waifu" / "database",
        waifu_db=tmp_path / ".waifu" / "database" / "waifu.db",
        db_backup_dir=tmp_path / ".waifu" / "db_backup",
        dreamsim_model_root=tmp_path / ".waifu" / "dreamsim_models",
    )


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, app_paths: AppPaths) -> Path:
    monkeypatch.setattr(connection, "PATHS", app_paths)
    monkeypatch.setattr(connection, "DB_PATH", app_paths.waifu_db)
    return app_paths.waifu_db


@pytest.fixture
def db_conn(isolated_db: Path):
    with closing(connection.open_connection(isolated_db)) as conn:
        yield conn


@pytest.fixture
def make_progress():
    def factory(total: int, desc: str) -> FakeProgressReporter:
        return FakeProgressReporter(total=total, desc=desc)

    return factory
