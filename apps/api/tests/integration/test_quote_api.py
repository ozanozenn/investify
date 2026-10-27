"""GET /api/companies/{ticker}/quote — önbellek, stale yedek, snapshot'sız çalışma."""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from app.main import app
from app.services.cache import RedisJsonCache, get_cache


class InMemoryCache:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}
        self.ttls: dict[str, int] = {}

    async def get_json(self, key: str) -> Any | None:
        return self.store.get(key)

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        self.store[key] = value
        self.ttls[key] = ttl_seconds


@pytest.fixture
def memory_cache():
    cache = InMemoryCache()
    app.dependency_overrides[get_cache] = lambda: cache
    return cache  # `client` fixture'ı override'ları test sonunda temizler


@pytest.fixture
def quote_calls(fake_providers, monkeypatch):
    """Sağlayıcıya kaç kez gidildiğini sayar (davranışı değiştirmeden)."""
    calls: list[str] = []
    original = fake_providers.market.get_quote

    async def counting(ticker: str):
        calls.append(ticker)
        return await original(ticker)

    monkeypatch.setattr(fake_providers.market, "get_quote", counting)
    return calls


async def test_second_call_is_served_from_cache(client, memory_cache, quote_calls):
    first = await client.get("/api/companies/test/quote")
    second = await client.get("/api/companies/TEST/quote")

    assert first.status_code == 200 and second.status_code == 200
    a, b = first.json(), second.json()
    assert a["is_cached"] is False and b["is_cached"] is True
    assert a["stale"] is False
    assert a["price"] == b["price"] == 50.0
    assert a["source"] == "fake"
    assert a["ticker"] == "TEST"
    assert "gecikmeli" in a["delay_note"]
    assert quote_calls == ["TEST"]  # ikinci istek sağlayıcıya gitmedi
    assert memory_cache.ttls == {"quote:v1:TEST": 60}  # Settings varsayılanı


async def test_change_vs_previous_close_is_computed_in_backend(client, memory_cache, fake_providers, monkeypatch):
    original = fake_providers.market.get_quote

    async def with_previous_close(ticker: str):
        return dataclasses.replace(await original(ticker), previous_close=40.0)

    monkeypatch.setattr(fake_providers.market, "get_quote", with_previous_close)

    body = (await client.get("/api/companies/TEST/quote")).json()
    assert body["previous_close"] == 40.0
    assert body["change"] == pytest.approx(10.0)
    assert body["change_fraction"] == pytest.approx(0.25)
    assert body["direction"] == "up"


async def test_without_previous_close_change_is_absent(client, memory_cache):
    body = (await client.get("/api/companies/TEST/quote")).json()
    assert body["previous_close"] is None
    assert body["change"] is None and body["change_fraction"] is None and body["direction"] is None


async def test_provider_failure_falls_back_to_snapshot_price_marked_stale(client, memory_cache, fake_providers):
    refresh = await client.post("/api/companies/TEST/refresh")
    assert refresh.status_code == 200
    snapshot_market = refresh.json()["market"]

    fake_providers.market.fail = True
    resp = await client.get("/api/companies/TEST/quote")

    assert resp.status_code == 200
    body = resp.json()
    assert body["stale"] is True
    assert body["is_cached"] is False
    assert body["source"] == "snapshot"
    assert body["price"] == snapshot_market["price"]
    assert body["as_of"] == snapshot_market["as_of"]  # snapshot'taki fiyatın zamanı
    assert body["stale_note"]
    assert memory_cache.store == {}  # yedek önbelleğe yazılmaz

    # Sağlayıcı dönünce bir sonraki istek yine canlı fiyatı alır.
    fake_providers.market.fail = False
    live = (await client.get("/api/companies/TEST/quote")).json()
    assert live["stale"] is False and live["source"] == "fake"


async def test_provider_failure_without_snapshot_is_503_in_turkish(client, memory_cache, fake_providers):
    fake_providers.market.fail = True
    resp = await client.get("/api/companies/NOSNAP/quote")
    assert resp.status_code == 503
    assert "güncel fiyat şu anda alınamıyor" in resp.json()["detail"]


async def test_quote_does_not_create_an_analysis_snapshot(client, memory_cache):
    assert (await client.get("/api/companies/FRESH/quote")).status_code == 200
    history = await client.get("/api/companies/FRESH/analysis/history")
    assert history.json() == []


async def test_unreachable_redis_never_fails_the_request(client, quote_calls):
    app.dependency_overrides[get_cache] = lambda: RedisJsonCache("redis://127.0.0.1:1/0")

    first = await client.get("/api/companies/TEST/quote")
    second = await client.get("/api/companies/TEST/quote")

    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["is_cached"] is False and second.json()["is_cached"] is False
    assert quote_calls == ["TEST", "TEST"]  # önbellek yok gibi davranır
