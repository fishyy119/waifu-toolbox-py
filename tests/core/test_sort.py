import importlib
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import numpy as np
import pytest

import waifu_toolbox.core as core_package
from tests.helpers import create_image, create_text_file
from waifu_toolbox.db.connection import Database
from waifu_toolbox.utils.feature import FeatureResult
from waifu_toolbox.utils.progress import ProgressFactory

pytestmark = pytest.mark.integration


def _load_sort_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    # 这些测试验证文件改名策略，不应初始化测试范围外的 UMAP 运行时。
    monkeypatch.setitem(sys.modules, "umap", ModuleType("umap"))
    # 模块缓存和包属性也需要还原，避免影响后续测试的导入。
    monkeypatch.setitem(sys.modules, "waifu_toolbox.core.sort", None)
    monkeypatch.delitem(sys.modules, "waifu_toolbox.core.sort")
    monkeypatch.setattr(core_package, "sort", None, raising=False)
    return importlib.import_module("waifu_toolbox.core.sort")


def test_get_sort_units_rules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "images"
    create_image(root / "root.png")
    create_image(root / "alpha" / "1.png")
    create_image(root / "beta" / "1.png")
    create_image(root / "beta" / "nested" / "1.png")
    create_image(root / "gamma" / "1.png")
    create_text_file(root / "gamma" / ".nosort")
    create_image(root / "gamma" / "nested" / "1.png")

    sort_module = _load_sort_module(monkeypatch)
    sort_units = set(sort_module.get_sort_units(root))

    assert sort_units == {
        root,
        root / "alpha",
        root / "beta",
        root / "beta" / "nested",
        root / "gamma" / "nested",
    }


def test_has_uniform_prefix_checks_against_parent_directory_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    unit = tmp_path / "alice"
    unit.mkdir(parents=True, exist_ok=True)

    matching = [
        unit / "alice_0000.png",
        unit / "alice_0001.png",
    ]
    mixed = [*matching, unit / "other_0002.png"]
    sort_module = _load_sort_module(monkeypatch)

    assert sort_module.has_uniform_prefix(matching) is True
    assert sort_module.has_uniform_prefix(mixed) is False


def test_sort_preserves_protected_directories(
    tmp_path: Path,
    database: Database,
    make_progress: ProgressFactory,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "images"
    protected = root / "protected"
    create_image(protected / "one.png", color=(255, 0, 0))
    create_image(protected / "two.png", color=(0, 255, 0))
    create_image(protected / "three.png", color=(0, 0, 255))
    create_text_file(protected / ".nosort")

    already_sorted = root / "alice"
    create_image(already_sorted / "alice_0000.png", color=(255, 0, 0))
    create_image(already_sorted / "alice_0001.png", color=(0, 255, 0))
    create_image(already_sorted / "alice_0002.png", color=(0, 0, 255))

    before = {path: path.read_bytes() for path in root.rglob("*.png")}
    sort_module = _load_sort_module(monkeypatch)
    extract_features = Mock(side_effect=AssertionError("受保护目录不应提取特征"))
    monkeypatch.setattr(sort_module, "get_image_features_use_cache", extract_features)

    result = sort_module.sort_images_by_perceptual_similarity(
        root,
        avoid_sorted=True,
        make_progress=make_progress,
    )

    assert result.ok is True
    assert {path: path.read_bytes() for path in root.rglob("*.png")} == before
    extract_features.assert_not_called()


def test_sort_renames_files_in_computed_order(
    tmp_path: Path,
    database: Database,
    make_progress: ProgressFactory,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "images"
    unit = root / "alice"
    paths = [
        create_image(unit / "a.png", color=(255, 0, 0)),
        create_image(unit / "b.png", color=(0, 255, 0)),
        create_image(unit / "c.png", color=(0, 0, 255)),
    ]
    contents = [path.read_bytes() for path in paths]

    sort_module = _load_sort_module(monkeypatch)
    monkeypatch.setattr(
        sort_module,
        "get_image_features_use_cache",
        Mock(return_value=FeatureResult([np.array([1.0], dtype=np.float32)] * 3, paths)),
    )
    monkeypatch.setattr(
        sort_module,
        "compute_dreamsim_distance_matrix",
        Mock(return_value=np.zeros((3, 3), dtype=np.float32)),
    )
    monkeypatch.setattr(sort_module, "umap_order", Mock(return_value=[2, 0, 1]))

    result = sort_module.sort_images_by_perceptual_similarity(
        root,
        avoid_sorted=False,
        make_progress=make_progress,
    )

    assert result.ok is True

    assert sorted(path.name for path in unit.iterdir()) == [
        "alice_0000.png",
        "alice_0001.png",
        "alice_0002.png",
    ]
    assert (unit / "alice_0000.png").read_bytes() == contents[2]
    assert (unit / "alice_0001.png").read_bytes() == contents[0]
    assert (unit / "alice_0002.png").read_bytes() == contents[1]
