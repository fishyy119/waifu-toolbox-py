from pathlib import Path
from sqlite3 import Connection
from unittest.mock import Mock

import numpy as np
import pytest

from waifu_toolbox.db.cache import CacheManager
from waifu_toolbox.utils import feature as feature_module
from waifu_toolbox.utils.progress import ProgressFactory

pytestmark = pytest.mark.integration


def test_get_image_features_use_cache_uses_cached_values_before_extracting(
    tmp_path: Path,
    db_conn: Connection,
    make_progress: ProgressFactory,
    monkeypatch: pytest.MonkeyPatch,
):
    cache = CacheManager(db_conn)

    hit_path = tmp_path / "hit.png"
    miss_path = tmp_path / "miss.png"
    hit_path.write_bytes(b"hit")
    miss_path.write_bytes(b"miss")

    hit_hash = b"hash-hit"
    miss_hash = b"hash-miss"
    cached_value = np.array([1.0, 0.0], dtype=np.float32)
    extracted_value = np.array([0.0, 1.0], dtype=np.float32)
    cache.set("dreamsim", hit_hash, cached_value)
    cache.save_cache("dreamsim")

    extract_feature = Mock(name="extract_feature", return_value=extracted_value)
    get_feature_extractor = Mock(name="get_feature_extractor", return_value=extract_feature)
    monkeypatch.setattr(feature_module, "_get_feature_extractor", get_feature_extractor)
    result = feature_module.get_image_features_use_cache(
        "dreamsim",
        paths_and_hashes=feature_module.PathsWithHashes(
            [hit_path, miss_path],
            [hit_hash, miss_hash],
        ),
        cache=cache,
        make_progress=make_progress,
    )

    get_feature_extractor.assert_called_once_with("dreamsim")
    extract_feature.assert_called_once_with(miss_path)
    assert result.paths == [hit_path, miss_path]
    assert np.array_equal(result.features[0], cached_value)
    assert np.array_equal(result.features[1], extracted_value)
