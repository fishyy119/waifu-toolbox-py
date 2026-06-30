from pathlib import Path

import pytest

from tests.helpers import create_image
from waifu_toolbox.db.analysis import FileStat, analyze_repo
from waifu_toolbox.db.operations import create_repo

pytestmark = pytest.mark.integration


def test_file_stat_from_files_counts_files_and_size(tmp_path: Path):
    first = create_image(tmp_path / "one.png")
    second = create_image(tmp_path / "two.png")

    stat = FileStat.from_files([first, second])

    assert stat.count == 2
    assert stat.size == first.stat().st_size + second.stat().st_size


def test_analyze_repo_by_extension_reports_expected_counts(tmp_path: Path, isolated_db: Path):
    repo_root = tmp_path / "repo"
    create_image(repo_root / "alice" / "one.png")
    create_image(repo_root / "bob" / "two.jpg")
    assert create_repo("chars", repo_root).ok is True

    result = analyze_repo("chars", type="extension")

    assert result.ok is True
    assert result.data is not None
    assert result.data["*.png"].count == 1
    assert result.data["*.jpg"].count == 1
    assert result.data["*.webp"].count == 0


def test_analyze_repo_by_category_reports_expected_counts(tmp_path: Path, isolated_db: Path):
    repo_root = tmp_path / "repo"
    create_image(repo_root / "alice" / "one.png")
    create_image(repo_root / "bob" / "two.png")
    assert create_repo("chars", repo_root).ok is True

    result = analyze_repo("chars", type="category")

    assert result.ok is True
    assert result.data is not None
    counts = {name: stat.count for name, stat in result.data.items()}
    assert counts == {"alice": 1, "bob": 1}
