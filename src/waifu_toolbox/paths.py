from dataclasses import dataclass
from pathlib import Path
from typing import Final


@dataclass(frozen=True, slots=True)
class AppPaths:
    waifu_home: Path
    database_root: Path
    waifu_db: Path
    db_backup_dir: Path
    dreamsim_model_root: Path

    def __post_init__(self) -> None:
        self.waifu_home.mkdir(parents=True, exist_ok=True)
        self.database_root.mkdir(parents=True, exist_ok=True)
        self.db_backup_dir.mkdir(parents=True, exist_ok=True)
        self.dreamsim_model_root.mkdir(parents=True, exist_ok=True)


_waifu_home = Path.home() / ".waifu"
_database_root = _waifu_home / "database"

PATHS: Final[AppPaths] = AppPaths(
    waifu_home=_waifu_home,
    database_root=_database_root,
    waifu_db=_database_root / "waifu.db",
    db_backup_dir=_waifu_home / "db_backup",
    dreamsim_model_root=_waifu_home / "dreamsim_models",
)
