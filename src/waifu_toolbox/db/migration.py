from importlib.resources import as_file, files

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine


def run_migrations(engine: Engine) -> None:
    """将数据库结构静默升级到 Alembic head。"""
    migration_scripts = files("waifu_toolbox.db").joinpath("migrations")
    # 迁移直接使用引擎，避免再次进入 Database 的初始化入口。
    with as_file(migration_scripts) as migration_path, engine.begin() as connection:
        config = Config()
        config.set_main_option("script_location", str(migration_path))
        migration_url = engine.url.render_as_string(hide_password=False).replace("%", "%%")
        config.set_main_option("sqlalchemy.url", migration_url)
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
