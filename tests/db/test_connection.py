import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from waifu_toolbox.db import connection
from waifu_toolbox.paths import AppPaths

pytestmark = pytest.mark.integration


def test_open_and_init_creates_schema_and_sets_user_version(isolated_db: Path):
    conn = connection.open_connection(isolated_db)
    with closing(conn) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
        assert {"repos", "images", "feature_cache"} <= tables
        assert conn.execute("PRAGMA user_version").fetchone()[0] == connection.SCHEMA_VERSION

        repo_columns = {row[1] for row in conn.execute("PRAGMA table_info(repos)").fetchall()}
        assert {"repo_id", "name", "path"} <= repo_columns

        image_columns = {row[1] for row in conn.execute("PRAGMA table_info(images)").fetchall()}
        assert {"repo_id", "hash", "label", "ccip_feature", "dreamsim_feature", "relative_path"} <= image_columns

        cache_columns = {row[1] for row in conn.execute("PRAGMA table_info(feature_cache)").fetchall()}
        assert {"hash", "feature_type", "feature"} <= cache_columns


def test_open_and_init_migrates_v1_schema_and_creates_backup(isolated_db: Path, app_paths: AppPaths):
    conn = sqlite3.connect(str(isolated_db))
    with closing(conn) as conn:
        conn.executescript("""
            CREATE TABLE repos (
                repo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL
            );

            CREATE TABLE images (
                repo_id INTEGER NOT NULL REFERENCES repos(repo_id) ON DELETE CASCADE,
                hash BLOB NOT NULL,
                label TEXT NOT NULL,
                ccip_feature BLOB,
                dreamsim_feature BLOB,
                UNIQUE (repo_id, hash)
            );

            CREATE TABLE feature_cache (
                hash BLOB NOT NULL,
                feature_type TEXT NOT NULL,
                feature BLOB NOT NULL,
                PRIMARY KEY (hash, feature_type)
            );

            PRAGMA user_version = 1;
            """)
        conn.commit()

    migrated = connection.open_connection(isolated_db)
    with closing(migrated) as migrated:
        assert migrated.execute("PRAGMA user_version").fetchone()[0] == connection.SCHEMA_VERSION

    backups = list(app_paths.db_backup_dir.glob(f"{isolated_db.stem}.v1.*{isolated_db.suffix}"))
    assert len(backups) == 1
