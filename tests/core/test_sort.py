from pathlib import Path

import pytest

from tests.helpers import create_image, create_text_file
from waifu_toolbox.core.sort import get_sort_units, has_uniform_prefix

pytestmark = pytest.mark.integration


def test_get_sort_units_rules(tmp_path: Path):
    root = tmp_path / "images"
    create_image(root / "root.png")
    create_image(root / "alpha" / "1.png")
    create_image(root / "beta" / "1.png")
    create_image(root / "beta" / "nested" / "1.png")
    create_image(root / "gamma" / "1.png")
    create_text_file(root / "gamma" / ".nosort")
    create_image(root / "gamma" / "nested" / "1.png")

    sort_units = set(get_sort_units(root))

    assert sort_units == {
        root,
        root / "alpha",
        root / "beta",
        root / "beta" / "nested",
        root / "gamma" / "nested",
    }


def test_has_uniform_prefix_checks_against_parent_directory_name(tmp_path: Path):
    unit = tmp_path / "alice"
    unit.mkdir(parents=True, exist_ok=True)

    matching = [
        unit / "alice_0000.png",
        unit / "alice_0001.png",
    ]
    mixed = [*matching, unit / "other_0002.png"]

    assert has_uniform_prefix(matching) is True
    assert has_uniform_prefix(mixed) is False
