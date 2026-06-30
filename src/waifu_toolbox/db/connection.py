import sqlite3
from datetime import datetime
from pathlib import Path

from ..paths import PATHS

DB_PATH: Path = PATHS.waifu_db

SCHEMA_VERSION = 2


def open_connection(path: Path | None = None) -> sqlite3.Connection:
    return _open_and_init(path or DB_PATH)


def _open_and_init(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    _migrate_schema(conn)
    return conn


def _backup_database(conn: sqlite3.Connection, current_version: int) -> None:
    """升级前自动备份数据库文件到"""
    backup_dir = PATHS.db_backup_dir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{DB_PATH.stem}.v{current_version}.{timestamp}{DB_PATH.suffix}"
    backup_path = backup_dir / backup_name

    backup_conn = sqlite3.connect(str(backup_path))
    conn.backup(backup_conn)
    backup_conn.close()


def _migrate_schema(conn: sqlite3.Connection) -> None:
    current: int = conn.execute("PRAGMA user_version").fetchone()[0]

    if current < SCHEMA_VERSION and current > 0:
        _backup_database(conn, current)

    if current < 1:
        _init_v1(conn)
    if current < 2:
        _migrate_v1_to_v2(conn)

    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()


def _migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(images)").fetchall()}
    if "relative_path" not in cols:
        conn.execute("ALTER TABLE images ADD COLUMN relative_path TEXT")


def _init_v1(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS repos (
            repo_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL UNIQUE,
            path      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS images (
            repo_id          INTEGER NOT NULL REFERENCES repos(repo_id) ON DELETE CASCADE,
            hash             BLOB    NOT NULL,
            label            TEXT    NOT NULL,
            ccip_feature     BLOB,
            dreamsim_feature BLOB,
            UNIQUE (repo_id, hash)
        );

        CREATE INDEX IF NOT EXISTS idx_images_repo ON images(repo_id);
        CREATE INDEX IF NOT EXISTS idx_images_hash ON images(hash);

        CREATE TABLE IF NOT EXISTS feature_cache (
            hash          BLOB    NOT NULL,
            feature_type  TEXT    NOT NULL,
            feature       BLOB    NOT NULL,
            PRIMARY KEY (hash, feature_type)
        );
    """)
