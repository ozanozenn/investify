"""yfinance `info` -> Quote: önceki kapanış ve borsa zamanı (ağ yok, sahte Ticker)."""

from __future__ import annotations

import datetime as dt

from app.providers.market import yfinance_provider
from app.providers.market.yfinance_provider import YFinanceMarketDataProvider


class _FakeTicker:
    def __init__(self, info: dict) -> None:
        self.info = info


def _quote(monkeypatch, info: dict):
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", lambda symbol: _FakeTicker(info))
    return YFinanceMarketDataProvider()._get_quote_sync("thyao")


def test_previous_close_and_market_time_are_parsed(monkeypatch):
    quote = _quote(
        monkeypatch,
        {"currentPrice": 312.5, "regularMarketPreviousClose": 300.0, "regularMarketTime": 1793100000, "currency": "TRY"},
    )
    assert quote.price == 312.5
    assert quote.previous_close == 300.0
    assert quote.market_time == dt.datetime.fromtimestamp(1793100000, tz=dt.timezone.utc)


def test_falls_back_to_previous_close_key(monkeypatch):
    quote = _quote(monkeypatch, {"regularMarketPrice": 10.0, "previousClose": 9.5})
    assert quote.previous_close == 9.5


def test_missing_fields_stay_none_instead_of_guessing(monkeypatch):
    quote = _quote(monkeypatch, {"currentPrice": 10.0, "regularMarketTime": "bozuk"})
    assert quote.previous_close is None
    assert quote.market_time is None
