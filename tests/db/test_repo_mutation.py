import shutil
from pathlib import Path
from sqlite3 import Connection

import numpy as np
import pytest

from tests.helpers import create_image
from waifu_toolbox.db.repo import ImageRepo

pytestmark = pytest.mark.integration


def test_deduplicate_removes_extra_copies_within_same_label(tmp_path: Path, db_conn: Connection):
    repo_root = tmp_path / "repo"
    original = create_image(repo_root / "alice" / "one.png")
    shutil.copy2(original, repo_root / "alice" / "dup.png")

    repo = ImageRepo(db_conn)
    assert repo.scan_init("chars", repo_root).ok is True
    repo.save()

    result = repo.deduplicate("chars")

    assert result.deleted == 1
    assert result.label_mismatches == []
    assert len(list((repo_root / "alice").glob("*.png"))) == 1


def test_deduplicate_reports_cross_label_mismatches_without_deleting(tmp_path: Path, db_conn: Connection):
    repo_root = tmp_path / "repo"
    original = create_image(repo_root / "alice" / "shared.png")
    duplicate = repo_root / "bob" / "shared.png"
    duplicate.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, duplicate)

    repo = ImageRepo(db_conn)
    assert repo.scan_init("chars", repo_root).ok is True
    repo.save()

    result = repo.deduplicate("chars")

    assert result.deleted == 0
    assert len(result.label_mismatches) == 1
    assert (repo_root / "alice" / "shared.png").exists()
    assert (repo_root / "bob" / "shared.png").exists()


def test_load_features_filters_rows_without_requested_feature(tmp_path: Path, db_conn: Connection):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    with db_conn:
        db_conn.execute("INSERT INTO repos (name, path) VALUES (?, ?)", ("chars", str(repo_root)))
        repo_id = db_conn.execute("SELECT repo_id FROM repos WHERE name = ?", ("chars",)).fetchone()[0]
        db_conn.executemany(
            """
            INSERT INTO images (repo_id, hash, label, relative_path, ccip_feature, dreamsim_feature)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    repo_id,
                    b"hash-a",
                    "alice",
                    "alice/one.png",
                    np.array([1.0, 2.0], dtype=np.float32).tobytes(),
                    None,
                ),
                (
                    repo_id,
                    b"hash-b",
                    "bob",
                    "bob/two.png",
                    None,
                    None,
                ),
            ],
        )

    repo = ImageRepo(db_conn, "chars")
    repo.load_features(ccip=True)

    assert repo.ccip_features is not None
    assert repo.ccip_features.shape == (1, 2)
    assert repo.labels == ["alice"]
    assert repo.relative_paths == ["alice/one.png"]
