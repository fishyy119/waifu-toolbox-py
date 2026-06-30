from pathlib import Path

import pytest

from tests.helpers import create_image
from waifu_toolbox.db.operations import (
    check_name,
    create_repo,
    delete_repo,
    flatten_repo,
    list_repo_infos,
    rename_repo,
)

pytestmark = pytest.mark.integration


def test_check_name_validation():
    assert check_name("") is not None
    assert check_name("中文") is not None
    assert check_name("bad-name") is not None
    assert check_name("!!!@@@###$$$") is not None
    assert check_name("chars_01") is None


def test_create_rename_and_delete_repo_round_trip(tmp_path: Path, isolated_db: Path):
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


def test_flatten_repo_copies_nested_files_by_top_level_label(tmp_path: Path, isolated_db: Path):
    repo_root = tmp_path / "repo"
    create_image(repo_root / "alice" / "nested" / "one.png")
    create_image(repo_root / "bob" / "two.png")

    assert create_repo("chars", repo_root).ok is True

    result = flatten_repo("chars")

    assert result.ok is True
    assert result.data is not None
    assert (result.data / "alice" / "one.png").exists()
    assert (result.data / "bob" / "two.png").exists()
