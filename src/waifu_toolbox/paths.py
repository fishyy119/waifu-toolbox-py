import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final


@dataclass(frozen=True, slots=True)
class AppPaths:
    waifu_home: Path
    database_root: Path
    waifu_db: Path
    dreamsim_model_root: Path


_waifu_home = Path(os.environ.get("WAIFU_HOME", Path.home() / ".waifu")).expanduser().resolve()
_database_root = _waifu_home / "database"

PATHS: Final[AppPaths] = AppPaths(
    waifu_home=_waifu_home,
    database_root=_database_root,
    waifu_db=_database_root / "waifu.db",
    dreamsim_model_root=_waifu_home / "dreamsim_models",
)
