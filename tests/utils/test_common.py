from pathlib import Path

import numpy as np
import pytest

from waifu_toolbox.utils.common import compute_file_hash, farthest_point_sampling


def test_compute_file_hash_changes_with_file_contents(tmp_path: Path):
    path = tmp_path / "sample.bin"
    path.write_bytes(b"alpha")
    first = compute_file_hash(path)

    path.write_bytes(b"beta")
    second = compute_file_hash(path)

    assert first != second


@pytest.mark.parametrize("k", [3, 5], ids=["equal-population", "exceeds-population"])
def test_farthest_point_sampling_returns_all_indices_when_k_exceeds_population(k: int):
    distances = np.zeros((3, 3), dtype=np.float32)
    result = farthest_point_sampling(distances, k)

    assert result == [0, 1, 2]


def test_farthest_point_sampling_returns_correct_unique_indices():
    distances = np.array(
        [
            [0.0, 1.0, 3.0, 4.0],
            [1.0, 0.0, 2.0, 5.0],
            [3.0, 2.0, 0.0, 6.0],
            [4.0, 5.0, 6.0, 0.0],
        ],
        dtype=np.float32,
    )
    result = farthest_point_sampling(distances, 3)

    assert result == [3, 2, 0]
