from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import IntegrityError

from waifu_toolbox.db import connection, migration
from waifu_toolbox.db.connection import Database
from waifu_toolbox.db.engine import create_sqlite_engine
from waifu_toolbox.db.operations import list_repos
from waifu_toolbox.db.schema import images, repos

pytestmark = pytest.mark.integration


def test_database_disposes_engine_when_initialization_fails(isolated_db: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_sqlite_engine(isolated_db)
    dispose_engine = Mock(wraps=engine.dispose)
    monkeypatch.setattr(connection, "create_sqlite_engine", Mock(return_value=engine))
    monkeypatch.setattr(migration, "run_migrations", Mock(side_effect=RuntimeError("initialization failed")))
    monkeypatch.setattr(engine, "dispose", dispose_engine)

    with pytest.raises(RuntimeError, match="initialization failed"):
        Database(isolated_db)
    dispose_engine.assert_called_once_with()


def test_database_can_reopen_after_close(database: Database):
    with database.begin() as conn:
        conn.execute(repos.insert().values(name="chars", path="C:/repo"))

    database.close()

    with database.connect() as conn:
        assert conn.execute(repos.select()).one().name == "chars"


def test_database_begin_rolls_back_when_scope_raises(database: Database):
    with pytest.raises(ValueError, match="abort transaction"), database.begin() as conn:
        conn.execute(repos.insert().values(name="chars", path="C:/repo"))
        raise ValueError("abort transaction")

    with database.connect() as conn:
        assert conn.execute(repos.select()).all() == []


def test_database_enforces_foreign_keys(database: Database):
    with (
        pytest.raises(IntegrityError, match="FOREIGN KEY constraint failed"),
        database.begin() as conn,
    ):
        conn.execute(images.insert().values(repo_id=999, hash=b"orphan", label="alice"))


def test_database_connect_does_not_commit_uncommitted_writes(database: Database):
    with database.connect() as conn:
        conn.execute(repos.insert().values(name="chars", path="C:/repo"))

    with database.connect() as conn:
        assert conn.execute(repos.select()).all() == []


def test_databases_keep_independent_contents(database: Database, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    other_database = Database(tmp_path / "other.db")
    try:
        with database.begin() as conn:
            conn.execute(repos.insert().values(name="first", path="C:/first"))
        with other_database.begin() as conn:
            conn.execute(repos.insert().values(name="second", path="C:/second"))

        with database.connect() as conn:
            assert conn.execute(repos.select()).one().name == "first"
        with other_database.connect() as conn:
            assert conn.execute(repos.select()).one().name == "second"

        assert [repo.name for repo in list_repos()] == ["first"]
        with monkeypatch.context() as patch:
            patch.setattr(connection, "database", other_database)
            assert [repo.name for repo in list_repos()] == ["second"]
        assert [repo.name for repo in list_repos()] == ["first"]
    finally:
        other_database.close()
