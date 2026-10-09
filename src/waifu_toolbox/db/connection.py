import atexit
from contextlib import AbstractContextManager
from pathlib import Path
from threading import Lock

from sqlalchemy.engine import Connection, Engine

from ..paths import PATHS
from . import migration
from .engine import create_sqlite_engine


class Database:
    """统一管理 SQLite 引擎的创建、迁移和关闭。"""

    def __init__(self, path: Path) -> None:
        """记录数据库路径，首次使用时创建引擎并完成迁移。"""
        self.path = path.expanduser().resolve()
        self._engine: Engine | None = None
        self._lock = Lock()

    @property
    def engine(self) -> Engine:
        with self._lock:
            if self._engine is None:
                engine = create_sqlite_engine(self.path)
                try:
                    migration.run_migrations(engine)
                except BaseException:
                    engine.dispose()
                    raise
                self._engine = engine
            return self._engine

    def connect(self) -> Connection:
        """打开连接，退出时释放连接；写入需要显式提交。"""
        return self.engine.connect()

    def begin(self) -> AbstractContextManager[Connection]:
        """打开一个事务作用域，正常退出时提交，异常退出时回滚。"""
        return self.engine.begin()

    def close(self) -> None:
        """释放引擎连接池中的空闲连接。"""
        with self._lock:
            if self._engine is not None:
                self._engine.dispose()
                self._engine = None


# 全局管理器按需创建数据库并迁移，进程退出时统一释放连接池。
database = Database(PATHS.waifu_db)
atexit.register(database.close)
