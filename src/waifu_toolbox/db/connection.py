import atexit
from contextlib import AbstractContextManager
from pathlib import Path

from sqlalchemy.engine import Connection

from ..paths import PATHS
from . import migration
from .engine import create_sqlite_engine


class Database:
    """管理 SQLite 引擎，并在创建实例时统一完成数据库迁移。"""

    def __init__(self, path: Path) -> None:
        """为指定 SQLite 文件创建 SQLAlchemy Engine，并完成数据库迁移。"""
        self.path = path.expanduser().resolve()
        self.engine = create_sqlite_engine(self.path)
        try:
            migration.run_migrations(self.engine)
        except BaseException:
            self.engine.dispose()
            raise

    def connect(self) -> Connection:
        """打开连接，退出时释放连接；写入需要显式提交。"""
        return self.engine.connect()

    def begin(self) -> AbstractContextManager[Connection]:
        """打开一个事务作用域，正常退出时提交，异常退出时回滚。"""
        return self.engine.begin()

    def close(self) -> None:
        """释放引擎连接池中的空闲连接。"""
        self.engine.dispose()


# 默认实例由本模块负责初始化，并在进程退出时释放。
database = Database(PATHS.waifu_db)
atexit.register(database.close)
