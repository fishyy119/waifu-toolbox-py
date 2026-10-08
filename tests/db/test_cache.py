import numpy as np
import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Connection

from waifu_toolbox.db.cache import CacheManager
from waifu_toolbox.db.connection import Database
from waifu_toolbox.db.schema import feature_cache

pytestmark = pytest.mark.integration


def test_cache_manager_returns_none_for_missing_values(db_conn: Connection):
    cache = CacheManager(db_conn)
    assert cache.get("ccip", b"missing") is None


def test_cache_manager_persists_values_on_save(database: Database):
    value = np.array([1.0, 2.0], dtype=np.float32)
    with database.begin() as conn:
        cache = CacheManager(conn)
        cache.set("ccip", b"image-hash", value)
        assert conn.execute(select(func.count()).select_from(feature_cache)).scalar_one() == 0
        cache.save_cache("ccip")

    with database.connect() as conn:
        stored = CacheManager(conn).get("ccip", b"image-hash")

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


def test_cache_upsert_is_isolated_by_feature_type(db_conn: Connection):
    cache = CacheManager(db_conn)
    ccip = np.array([1.0, 2.0], dtype=np.float32)
    dreamsim = np.array([3.0, 4.0], dtype=np.float32)

    cache.set("ccip", b"image-hash", ccip)
    cache.set("dreamsim", b"image-hash", dreamsim)
    cache.save_cache("ccip")
    cache.save_cache("dreamsim")

    replacement = np.array([5.0, 6.0], dtype=np.float32)
    cache.set("ccip", b"image-hash", replacement)
    cache.save_cache("ccip")

    reloaded = CacheManager(db_conn)
    stored_ccip = reloaded.get("ccip", b"image-hash")
    stored_dreamsim = reloaded.get("dreamsim", b"image-hash")
    assert stored_ccip is not None
    assert stored_dreamsim is not None
    assert np.array_equal(stored_ccip, replacement)
    assert np.array_equal(stored_dreamsim, dreamsim)
