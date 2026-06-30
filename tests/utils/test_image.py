from pathlib import Path

from tests.helpers import create_image
from waifu_toolbox.utils.image import load_image, load_images_from_folder


def test_load_image_converts_mode_and_resizes(tmp_path: Path):
    source = create_image(tmp_path / "wide.png", size=(512, 128), color=(0, 128, 255), mode="RGB")

    image = load_image(source, max_size=128, mode="RGBA")

    assert image.mode == "RGBA"
    assert max(image.size) <= 128


def test_load_images_from_folder_reads_root_and_first_level_subdirectories(tmp_path: Path):
    root = tmp_path / "images"
    create_image(root / "root.png")
    create_image(root / "group_a" / "a.png")
    create_image(root / "group_b" / "nested" / "b.png")

    loaded = load_images_from_folder(root)

    assert len(loaded.images) == 3
    assert set(loaded.paths) == {
        root / "root.png",
        root / "group_a" / "a.png",
        root / "group_b" / "nested" / "b.png",
    }
