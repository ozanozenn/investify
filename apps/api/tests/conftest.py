"""Tüm testler için ortak ortam ayarları ve fixture'lar.

Bu dosya alt dizinlerdeki conftest'lerden ve `app.main` import edilmeden
önce yüklenir; `get_settings()` önbelleğe alındığı için ayarlar burada,
ilk çağrıdan ve uygulama importlarından önce verilmelidir.
"""

from __future__ import annotations

import os

# İzleme listesi zamanlayıcısı testlerde asla çalışmaz (ADR-013).
os.environ["WATCHLIST_REFRESH_ENABLED"] = "false"

import pytest  # noqa: E402

from app.providers.company import ticker_index  # noqa: E402


@pytest.fixture(autouse=True)
def _static_ticker_index_only(monkeypatch, tmp_path):
    """Search tests must not depend on whether the generated
    `bist_companies.json` exists or how many companies it lists (ADR-015);
    tests that exercise the file pass their own path/index explicitly."""
    monkeypatch.setattr(ticker_index, "BIST_COMPANIES_PATH", tmp_path / "bist_companies.absent.json")
    ticker_index.get_ticker_index.cache_clear()
    yield
    ticker_index.get_ticker_index.cache_clear()
