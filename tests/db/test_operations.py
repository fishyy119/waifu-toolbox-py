import shutil
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import func, select

from tests.helpers import create_image
from waifu_toolbox.db.cache import CacheManager
from waifu_toolbox.db.connection import Database
from waifu_toolbox.db.operations import (
    check_name,
    create_repo,
    delete_repo,
    flatten_repo,
    list_repo_infos,
    rename_repo,
)
from waifu_toolbox.db.schema import feature_cache, images, repos
from waifu_toolbox.utils.common import compute_file_hash

pytestmark = pytest.mark.integration


def test_check_name_validation():
    assert check_name("") is not None
    assert check_name("中文") is not None
    assert check_name("bad-name") is not None
    assert check_name("!!!@@@###$$$") is not None
    assert check_name("chars_01") is None


def test_create_rename_and_delete_repo_round_trip(tmp_path: Path, database: Database):
    repo_root = tmp_path / "repo"
    create_image(repo_root / "alice" / "one.png")

    created = create_repo("chars", repo_root)
    assert created.ok is True

    infos = list_repo_infos()
    assert len(infos) == 1
    assert infos[0].name == "chars"
    assert infos[0].total_images == 1

    renamed = rename_repo("chars", "chars_v2")
    assert renamed.ok is True
    assert [info.name for info in list_repo_infos()] == ["chars_v2"]

    deleted = delete_repo("chars_v2")
    assert deleted.ok is True
    assert list_repo_infos() == []


def test_flatten_repo_copies_nested_files_by_top_level_label(tmp_path: Path, database: Database):
    repo_root = tmp_path / "repo"
    create_image(repo_root / "alice" / "nested" / "one.png")
    create_image(repo_root / "bob" / "two.png")

    assert create_repo("chars", repo_root).ok is True

    result = flatten_repo("chars")

    assert result.ok is True
    assert result.data is not None
    assert (result.data / "alice" / "one.png").exists()
    assert (result.data / "bob" / "two.png").exists()


def test_delete_repo_removes_only_owned_index(tmp_path: Path, database: Database):
    first_root = tmp_path / "first"
    first_image = create_image(first_root / "alice" / "shared.png")
    second_root = tmp_path / "second"
    second_image = second_root / "bob" / "shared.png"
    second_image.parent.mkdir(parents=True)
    shutil.copy2(first_image, second_image)

    assert create_repo("first", first_root).ok is True
    assert create_repo("second", second_root).ok is True

    image_hash = compute_file_hash(first_image)
    with database.begin() as conn:
        cache = CacheManager(conn)
        cache.set("ccip", image_hash, np.array([1.0], dtype=np.float32))
        cache.save_cache("ccip")

    assert delete_repo("first").ok is True

    with database.begin() as conn:
        assert conn.execute(select(repos.c.name)).scalars().all() == ["second"]
        assert conn.execute(select(func.count()).select_from(images)).scalar_one() == 1
        assert conn.execute(select(func.count()).select_from(feature_cache)).scalar_one() == 1
    assert first_image.exists()
    assert second_image.exists()


def test_flatten_repo_rejects_filename_collisions(tmp_path: Path, database: Database):
    repo_root = tmp_path / "repo"
    first = create_image(repo_root / "alice" / "first" / "same.png", color=(255, 0, 0))
    second = create_image(repo_root / "alice" / "second" / "same.png", color=(0, 255, 0))
    assert create_repo("chars", repo_root).ok is True

    result = flatten_repo("chars")

    assert result.ok is False
    assert "重复的文件名" in result.message
    assert first.exists()
    assert second.exists()
