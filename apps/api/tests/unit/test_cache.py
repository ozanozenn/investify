"""services/cache.py — Redis çalışmadan: sahte istemci + gerçekten kapalı port."""

from __future__ import annotations

import logging

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.services.cache import NullCache, RedisJsonCache

# Hiçbir şeyin dinlemediği port: gerçek redis.asyncio istemcisi bağlantı
# reddi alır (sunucu gerektirmeden "Redis kapalı" senaryosu).
_DEAD_REDIS_URL = "redis://127.0.0.1:1/0"


class FakeRedis:
    """`get`/`set(ex=...)` alt kümesi; istenirse ilk N çağrıda hata verir."""

    def __init__(self, fail_times: int = 0) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.calls = 0
        self._fail_times = fail_times

    def _maybe_fail(self) -> None:
        self.calls += 1
        if self._fail_times > 0:
            self._fail_times -= 1
            raise RedisConnectionError("bağlantı reddedildi")

    async def get(self, key: str) -> str | None:
        self._maybe_fail()
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._maybe_fail()
        self.store[key] = value
        self.ttls[key] = ex


def _warnings(caplog, message: str) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.getMessage() == message and r.levelno == logging.WARNING]


async def test_miss_returns_none():
    cache = RedisJsonCache("redis://unused", client=FakeRedis())
    assert await cache.get_json("yok") is None


async def test_set_then_get_is_a_hit_with_ttl():
    fake = FakeRedis()
    cache = RedisJsonCache("redis://unused", client=fake)

    await cache.set_json("quote:v1:TEST", {"price": 50.0, "note": "gecikmeli"}, ttl_seconds=60)

    assert await cache.get_json("quote:v1:TEST") == {"price": 50.0, "note": "gecikmeli"}
    assert fake.ttls["quote:v1:TEST"] == 60


async def test_unreadable_entry_is_treated_as_miss():
    fake = FakeRedis()
    fake.store["k"] = "{bozuk json"
    cache = RedisJsonCache("redis://unused", client=fake)
    assert await cache.get_json("k") is None


async def test_unreachable_redis_degrades_to_no_cache_and_warns_once(caplog):
    caplog.set_level(logging.INFO)
    # retry_after=0: her çağrı Redis'i yeniden dener — yine de tek uyarı.
    cache = RedisJsonCache(_DEAD_REDIS_URL, retry_after_seconds=0)

    for _ in range(3):
        await cache.set_json("k", {"a": 1}, ttl_seconds=60)  # istisna fırlatmaz
        assert await cache.get_json("k") is None

    assert len(_warnings(caplog, "cache_unavailable")) == 1


async def test_outage_skips_redis_until_retry_window_passes():
    fake = FakeRedis(fail_times=1)
    cache = RedisJsonCache("redis://unused", client=fake, retry_after_seconds=3600)

    assert await cache.get_json("k") is None  # hata -> kesinti penceresi açılır
    assert await cache.get_json("k") is None
    await cache.set_json("k", {"a": 1}, ttl_seconds=60)

    assert fake.calls == 1  # pencere içinde Redis'e hiç gidilmedi


async def test_recovery_is_logged_and_next_outage_warns_again(caplog):
    caplog.set_level(logging.INFO)
    fake = FakeRedis(fail_times=1)
    cache = RedisJsonCache("redis://unused", client=fake, retry_after_seconds=0)

    assert await cache.get_json("k") is None  # kesinti
    await cache.set_json("k", {"a": 1}, ttl_seconds=60)  # toparlandı
    assert await cache.get_json("k") == {"a": 1}
    assert any(r.getMessage() == "cache_recovered" for r in caplog.records)

    fake._fail_times = 1
    assert await cache.get_json("k") is None  # yeni kesinti -> yeni uyarı
    assert len(_warnings(caplog, "cache_unavailable")) == 2


async def test_null_cache_never_stores():
    cache = NullCache()
    await cache.set_json("k", {"a": 1}, ttl_seconds=60)
    assert await cache.get_json("k") is None


@pytest.mark.parametrize("ttl", [0, -5])
async def test_non_positive_ttl_is_clamped_to_one_second(ttl):
    fake = FakeRedis()
    cache = RedisJsonCache("redis://unused", client=fake)
    await cache.set_json("k", 1, ttl_seconds=ttl)
    assert fake.ttls["k"] == 1
