from __future__ import annotations

import pytest

from app.providers.company import ticker_index


@pytest.fixture(autouse=True)
def _static_ticker_index_only(monkeypatch, tmp_path):
    """Search tests must not depend on whether the generated
    `bist_companies.json` exists or how many companies it lists (ADR-015);
    tests that exercise the file pass their own path/index explicitly."""
    monkeypatch.setattr(ticker_index, "BIST_COMPANIES_PATH", tmp_path / "bist_companies.absent.json")
    ticker_index.get_ticker_index.cache_clear()
    yield
    ticker_index.get_ticker_index.cache_clear()
