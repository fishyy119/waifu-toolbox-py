import shutil
from pathlib import Path
from sqlite3 import Connection

import pytest

from tests.helpers import create_image
from waifu_toolbox.db.repo import ImageRepo
from waifu_toolbox.utils.progress import ProgressFactory

pytestmark = pytest.mark.integration


def test_scan_imgs_with_label_collects_only_category_directories(tmp_path: Path):
    repo_root = tmp_path / "repo"
    create_image(repo_root / "alice" / "one.png")
    create_image(repo_root / "bob" / "nested" / "two.png")
    create_image(repo_root / "ignored.png")

    result = ImageRepo.scan_imgs_with_label(repo_root)

    assert set(result.labels) == {"alice", "bob"}
    assert repo_root / "ignored.png" not in result.paths


def test_scan_init_deduplicates_same_label_duplicates(
    tmp_path: Path, db_conn: Connection, make_progress: ProgressFactory
):
    repo_root = tmp_path / "repo"
    original = create_image(repo_root / "alice" / "one.png", color=(255, 0, 0))
    duplicate = repo_root / "alice" / "copies" / "one_copy.png"
    duplicate.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, duplicate)
    create_image(repo_root / "bob" / "two.png", color=(0, 255, 0))

    repo = ImageRepo(db_conn)
    result = repo.scan_init("chars", repo_root, make_progress=make_progress)

    assert result.ok is True
    assert result.label_mismatches == []
    assert len(repo.hashes) == 2
    assert {Path(path).parts[0] for path in repo.relative_paths} == {"alice", "bob"}


def test_scan_init_reports_cross_label_duplicate_conflicts(tmp_path: Path, db_conn: Connection):
    repo_root = tmp_path / "repo"
    original = create_image(repo_root / "alice" / "shared.png", color=(255, 0, 0))
    duplicate = repo_root / "bob" / "shared.png"
    duplicate.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, duplicate)

    repo = ImageRepo(db_conn)
    result = repo.scan_init("chars", repo_root)

    assert result.ok is True
    assert len(repo.hashes) == 1
    assert len(result.label_mismatches) == 1
    assert "alice" in result.label_mismatches[0]
    assert "bob" in result.label_mismatches[0]


def test_scan_init_save_and_load_round_trip(tmp_path: Path, db_conn: Connection):
    repo_root = tmp_path / "repo"
    create_image(repo_root / "alice" / "one.png", color=(255, 0, 0))
    create_image(repo_root / "bob" / "two.png", color=(0, 255, 0))

    repo = ImageRepo(db_conn)
    result = repo.scan_init("chars", repo_root)
    assert result.ok is True
    repo.save()

    loaded = ImageRepo(db_conn)
    assert loaded.load("chars") is True
    assert loaded.repo_path == repo_root

    actual = {
        (label, Path(relative_path).as_posix()) for label, relative_path in zip(loaded.labels, loaded.relative_paths)
    }
    assert actual == {
        ("alice", "alice/one.png"),
        ("bob", "bob/two.png"),
    }
