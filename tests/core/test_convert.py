from pathlib import Path

import pytest
from PIL import features as pil_features

from tests.helpers import create_image, create_text_file
from waifu_toolbox.core.convert import collect_files, convert_images, convert_single

WEBP_SUPPORTED = pil_features.check("webp")

pytestmark = pytest.mark.integration


def test_collect_files_validates_input(tmp_path: Path):
    missing = tmp_path / "missing"
    with pytest.raises(FileNotFoundError):
        collect_files(missing, "*.bmp")

    plain_file = create_text_file(tmp_path / "sample.txt")
    with pytest.raises(NotADirectoryError):
        collect_files(plain_file, "*.bmp")


@pytest.mark.skipif(not WEBP_SUPPORTED, reason="Pillow build does not support WebP")
def test_convert_single_creates_webp_without_removing_source(tmp_path: Path):
    source = create_image(tmp_path / "sample.bmp")

    error = convert_single(source, replace=False)

    assert error is None
    assert source.exists()
    assert source.with_suffix(".webp").exists()


@pytest.mark.skipif(not WEBP_SUPPORTED, reason="Pillow build does not support WebP")
def test_convert_single_can_replace_source_file(tmp_path: Path):
    source = create_image(tmp_path / "sample.bmp")

    error = convert_single(source, replace=True)

    assert error is None
    assert not source.exists()
    assert source.with_suffix(".webp").exists()


def test_convert_images_returns_failure_result_for_missing_directory(tmp_path: Path):
    result = convert_images(tmp_path / "missing")

    assert result.ok is False
    assert "does not exist" in result.message
