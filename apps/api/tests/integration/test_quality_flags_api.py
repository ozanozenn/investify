"""Refresh pipeline kalite bayraklarını ve reel büyümeyi üretir, snapshot'a
yazar ve API'de döner (ADR-016)."""

from __future__ import annotations

import datetime as dt

import pytest

from app.providers.base import MacroObservationDTO, RawFinancialPeriod
from tests.integration.conftest import FakeCompanyProvider, FakeFinancialProvider, FakeMacroProvider


class RealCpiMacroProvider(FakeMacroProvider):
    """TCMB'den gelmiş gibi gerçek (is_mock=False) TÜFE: %30, Ocak 2026."""

    async def get_series(self, series_code: str, lookback_days: int = 400) -> list[MacroObservationDTO]:
        now = dt.datetime.now(dt.timezone.utc)
        return [
            MacroObservationDTO(
                series_code=series_code,
                observation_date=dt.date(2026, 1, 1),
                value=30.0,
                is_mock=False,
                fetched_at=now,
            )
        ]


class DeterioratingFinancialProvider(FakeFinancialProvider):
    """Gelir +%40, ama faaliyet nakit akışı düşüyor ve alacaklar şişiyor."""

    async def get_financial_statements(self, ticker, annual_years=5, quarterly_quarters=8):
        now = dt.datetime.now(dt.timezone.utc)

        def period(year: int, values: dict[str, float]) -> RawFinancialPeriod:
            return RawFinancialPeriod(
                period_type="ANNUAL",
                fiscal_year=year,
                fiscal_quarter=None,
                period_end_date=dt.date(year, 12, 31),
                currency="TRY",
                values=values,
                source_code=self.code,
                fetched_at=now,
            )

        common = {"CASH": 100.0, "TOTAL_ASSETS": 2000.0, "CAPEX": -50.0, "INVENTORY": 150.0}
        return [
            period(2024, {**common, "REVENUE": 1000.0, "EBITDA": 200.0, "NET_INCOME": 100.0, "EQUITY": 500.0,
                          "TOTAL_DEBT": 300.0, "OPERATING_CASH_FLOW": 150.0, "RECEIVABLES": 200.0}),
            period(2025, {**common, "REVENUE": 1400.0, "EBITDA": 280.0, "NET_INCOME": 140.0, "EQUITY": 640.0,
                          "TOTAL_DEBT": 400.0, "OPERATING_CASH_FLOW": 100.0, "RECEIVABLES": 400.0,
                          "INVENTORY": 210.0}),
        ]


@pytest.mark.asyncio
async def test_refresh_returns_quality_flags_and_persists_them(client):
    body = (await client.post("/api/companies/QUAL/refresh")).json()

    qf = body["quality_flags"]
    assert qf["as_of_period"] == "2025"
    assert qf["engine_version"] == "v1"
    assert qf["flags"] == []  # sahte şirket sağlıklı
    # Sahte sağlayıcıda alacak/stok yok -> tahmin edilmez, "değerlendirilemedi".
    not_evaluated = {c["key"]: c["missing_fields"] for c in qf["not_evaluated"]}
    assert not_evaluated == {"receivables_vs_revenue": ["RECEIVABLES"], "inventory_vs_revenue": ["INVENTORY"]}
    assert len(qf["passed_checks"]) == 7

    # Sahte makro sağlayıcı mock TÜFE döner -> reel büyüme yok, nominal var.
    rg = body["real_growth"]
    assert rg["missing_fields"] == ["cpi_yoy_mock"]
    assert rg["revenue_growth_real"] is None
    assert rg["revenue_growth_nominal"] == pytest.approx(0.1)

    cached = (await client.get("/api/companies/QUAL/analysis")).json()
    assert cached["quality_flags"] == qf
    assert cached["real_growth"] == rg


@pytest.mark.asyncio
async def test_refresh_flags_deteriorating_company_and_deflates_with_real_cpi(client, fake_providers):
    fake_providers.financial = DeterioratingFinancialProvider()
    fake_providers.macro = RealCpiMacroProvider()

    body = (await client.post("/api/companies/BOZUK/refresh")).json()

    keys = {f["key"]: f["severity"] for f in body["quality_flags"]["flags"]}
    assert keys["revenue_vs_cash"] == "UYARI"
    assert keys["earnings_vs_cash"] == "DIKKAT"
    assert keys["receivables_vs_revenue"] == "DIKKAT"
    assert "inventory_vs_revenue" not in keys  # stok gelirle aynı hızda

    rg = body["real_growth"]
    assert rg["missing_fields"] == []
    assert rg["cpi_yoy"] == pytest.approx(0.30)
    assert rg["revenue_growth_real"] == pytest.approx(1.4 / 1.3 - 1)
    assert rg["net_income_growth_real"] == pytest.approx(1.4 / 1.3 - 1)


@pytest.mark.asyncio
async def test_failed_financials_degrade_quality_flags(client, fake_providers):
    fake_providers.financial.fail = True
    body = (await client.post("/api/companies/BOS/refresh")).json()
    assert body["quality_flags"]["missing_fields"] == ["no_financial_periods"]
    assert body["quality_flags"]["flags"] == []
    assert body["real_growth"]["missing_fields"] == ["no_financial_periods"]


class FakeBankProvider(FakeCompanyProvider):
    async def get_company_profile(self, ticker: str) -> dict:
        return {**await super().get_company_profile(ticker), "is_financial_industry": True}


@pytest.mark.asyncio
async def test_unsupported_industry_skips_quality_flags(client, fake_providers):
    fake_providers.company = FakeBankProvider()
    body = (await client.post("/api/companies/BANKA/refresh")).json()
    assert body["unsupported_reason"]
    assert body["quality_flags"]["missing_fields"] == ["unsupported_industry"]
    assert body["real_growth"]["missing_fields"] == ["unsupported_industry"]
