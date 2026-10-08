from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy.engine import Connection, make_url

from waifu_toolbox.db.engine import create_sqlite_engine, sqlite_url
from waifu_toolbox.db.schema import metadata
from waifu_toolbox.paths import PATHS

config = context.config
target_metadata = metadata

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url") or sqlite_url(PATHS.waifu_db).render_as_string(hide_password=False)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_with_connection(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        _run_with_connection(supplied_connection)
        return

    url = make_url(config.get_main_option("sqlalchemy.url") or sqlite_url(PATHS.waifu_db))
    if url.database is None:
        raise RuntimeError("迁移配置缺少 SQLite 数据库路径")
    engine = create_sqlite_engine(Path(url.database))
    try:
        with engine.begin() as connection:
            _run_with_connection(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
