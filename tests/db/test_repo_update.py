from pathlib import Path
from sqlite3 import Connection

import pytest

from tests.helpers import create_image
from waifu_toolbox.db.repo import ImageRepo

pytestmark = pytest.mark.integration


def test_update_detects_new_images_and_label_changes(tmp_path: Path, db_conn: Connection):
    repo_root = tmp_path / "repo"
    original = create_image(repo_root / "alice" / "face.png", color=(255, 0, 0))

    repo = ImageRepo(db_conn)
    assert repo.scan_init("chars", repo_root).ok is True
    repo.save()

    moved = repo_root / "bob" / "face.png"
    moved.parent.mkdir(parents=True, exist_ok=True)
    original.replace(moved)
    create_image(repo_root / "alice" / "extra.png", color=(0, 255, 0))

    result = repo.update("chars")

    assert result.new_images == 1
    assert result.updated_labels == 1

    loaded = ImageRepo(db_conn)
    assert loaded.load("chars") is True

    actual = {
        (label, Path(relative_path).as_posix()) for label, relative_path in zip(loaded.labels, loaded.relative_paths)
    }
    assert actual == {
        ("alice", "alice/extra.png"),
        ("bob", "bob/face.png"),
    }


def test_purge_removes_rows_for_deleted_files(tmp_path: Path, db_conn: Connection):
    repo_root = tmp_path / "repo"
    create_image(repo_root / "alice" / "keep.png", color=(255, 0, 0))
    to_remove = create_image(repo_root / "alice" / "remove.png", color=(0, 255, 0))

    repo = ImageRepo(db_conn)
    assert repo.scan_init("chars", repo_root).ok is True
    repo.save()

    to_remove.unlink()
    removed = repo.purge("chars")

    assert removed == 1

    loaded = ImageRepo(db_conn)
    assert loaded.load("chars") is True
    assert Path(loaded.relative_paths[0]).as_posix() == "alice/keep.png"
