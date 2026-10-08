import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, Engine


def sqlite_url(path: Path) -> URL:
    return URL.create("sqlite+pysqlite", database=str(path))


def create_sqlite_engine(path: Path) -> Engine:
    """创建 SQLite 引擎，供数据库初始化和 Alembic 迁移共用。"""
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(sqlite_url(path), connect_args={"autocommit": False, "timeout": 5.0})
    event.listen(engine, "connect", _configure_sqlite)
    return engine


def _configure_sqlite(dbapi_connection: sqlite3.Connection, _connection_record: object) -> None:
    previous_autocommit = dbapi_connection.autocommit
    dbapi_connection.autocommit = True
    try:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA busy_timeout = 5000")
        finally:
            cursor.close()
    finally:
        dbapi_connection.autocommit = previous_autocommit
