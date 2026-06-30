from sqlite3 import Connection

import numpy as np
import pytest

from waifu_toolbox.db.cache import CacheManager

pytestmark = pytest.mark.integration


def test_cache_manager_returns_none_for_missing_values(db_conn: Connection):
    cache = CacheManager(db_conn)
    assert cache.get("ccip", b"missing") is None


def test_cache_manager_persists_values_on_save(db_conn: Connection):
    cache = CacheManager(db_conn)
    value = np.array([1.0, 2.0], dtype=np.float32)

    cache.set("ccip", b"image-hash", value)
    cache.save_cache("ccip")

    stored = cache.get("ccip", b"image-hash")
    assert stored is not None
    assert np.array_equal(stored, value)


def test_cache_manager_returns_independent_arrays_from_get(db_conn: Connection):
    cache = CacheManager(db_conn)
    cache.set("dreamsim", b"image-hash", np.array([3.0, 4.0], dtype=np.float32))
    cache.save_cache("dreamsim")

    stored = cache.get("dreamsim", b"image-hash")
    assert stored is not None
    stored[0] = 99.0

    reloaded = cache.get("dreamsim", b"image-hash")
    assert reloaded is not None
    assert reloaded[0] == pytest.approx(3.0)
