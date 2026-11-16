"""Composite financial provider wired through the real refresh pipeline
(ADR-015): fallback use and cross-check disagreements surface as Turkish
data-quality warnings, and the primary source's numbers are the ones used."""

from __future__ import annotations

import dataclasses

import pytest

from app.providers.base import ProviderUnavailableError
from app.providers.financial.composite_provider import CompositeFinancialDataProvider
from tests.integration.conftest import FakeFinancialProvider


class _NamedFake(FakeFinancialProvider):
    def __init__(self, code: str, revenue_factor: float = 1.0, fail: bool = False):
        self.code = code
        self.revenue_factor = revenue_factor
        self.fail = fail

    async def get_financial_statements(self, ticker, annual_years=5, quarterly_quarters=8):
        if self.fail:
            raise ProviderUnavailableError(self.code, "simulated failure")
        periods = await super().get_financial_statements(ticker, annual_years, quarterly_quarters)
        return [
            dataclasses.replace(
                p,
                source_code=self.code,
                values={**p.values, "REVENUE": p.values["REVENUE"] * self.revenue_factor},
            )
            for p in periods
        ]


def _composite(primary, fallback, cross_check):
    return CompositeFinancialDataProvider(
        primary,
        fallback,
        cross_check=cross_check,
        tolerance=0.05,
        cross_check_fields=["REVENUE", "NET_INCOME"],
        cross_check_period_types=["ANNUAL"],
    )


@pytest.mark.asyncio
async def test_fallback_source_is_used_and_reported(client, fake_providers):
    fake_providers.financial = _composite(
        _NamedFake("isyatirim", fail=True), _NamedFake("yfinance"), cross_check=False
    )

    body = (await client.post("/api/companies/FALLB/refresh")).json()

    assert body["stage_results"]["financials"] == "SUCCESS"
    assert body["metrics"]["as_of_period"] != "N/A"
    assert (
        "Birincil finansal tablo kaynağı (İş Yatırım) veri vermedi; yedek kaynak (Yahoo Finance) kullanıldı."
        in body["data_quality"]["warnings"]
    )


@pytest.mark.asyncio
async def test_cross_check_disagreement_becomes_data_quality_warning(client, fake_providers):
    fake_providers.financial = _composite(
        _NamedFake("isyatirim"), _NamedFake("yfinance", revenue_factor=1.5), cross_check=True
    )

    body = (await client.post("/api/companies/XCHK/refresh")).json()

    warnings = body["data_quality"]["warnings"]
    assert (
        "Finansal tablo çapraz kontrolü (2025 yıllık): Hasılat için İş Yatırım ile Yahoo Finance "
        "değerleri tolerans dışında farklı; İş Yatırım değerleri kullanıldı."
    ) in warnings
    # Primary (İş Yatırım) revenue drives the history, not the fallback's 1.5x figure.
    history = {p["fiscal_year"]: p["revenue"] for p in body["financial_history"]}
    assert history[2025] == pytest.approx(1331.0)
