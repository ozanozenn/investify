"""Banka uçtan uca akışı (ADR-014): sahte banka sağlayıcılarıyla refresh."""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select

from app.financial_engine.industry_strategy import (
    BANK_DCF_NOT_APPLICABLE_MESSAGE,
    UNSUPPORTED_INDUSTRY_MESSAGE,
)
from app.llm.context_formatter import format_context_for_prompt
from app.models.snapshots import AnalysisSnapshot
from app.providers.base import CompanyDataProvider, FinancialDataProvider, RawFinancialPeriod
from app.schemas.context import StructuredAnalysisContext


class FakeFinanceCompanyProvider(CompanyDataProvider):
    """BNK* → banka (ham yfinance taksonomisiyle), SGR* → sigorta, diğerleri sanayi."""

    code = "fake"

    async def get_company_profile(self, ticker: str) -> dict:
        if ticker.startswith("BNK"):
            return {"name": f"{ticker} Bankası A.Ş.", "sector": "Financial Services",
                    "industry": "Banks - Regional", "is_financial_industry": True}
        if ticker.startswith("SGR"):
            return {"name": f"{ticker} Sigorta A.Ş.", "sector": "Finans",
                    "industry": "Sigorta", "is_financial_industry": True}
        return {"name": f"{ticker} Test A.Ş.", "sector": "Sanayi",
                "industry": "Test Industry", "is_financial_industry": False}


def _bank_period(year: int, values: dict[str, float]) -> RawFinancialPeriod:
    return RawFinancialPeriod(
        period_type="ANNUAL", fiscal_year=year, fiscal_quarter=None,
        period_end_date=dt.date(year, 12, 31), currency="TRY", values=values,
        source_code="fake", fetched_at=dt.datetime.now(dt.timezone.utc),
    )


class FakeBankFinancialProvider(FinancialDataProvider):
    """Banka benzeri tablo: hasılat/FAVÖK yok, net faiz geliri var. Nakit akışı
    bilerek tuhaf (mevduat hareketleri) — banka motoru bunu kullanmamalı."""

    code = "fake"

    async def get_financial_statements(self, ticker, annual_years=5, quarterly_quarters=8):
        return [
            _bank_period(2024, {
                "NET_INCOME": 600.0, "EQUITY": 3000.0, "TOTAL_ASSETS": 30000.0,
                "NET_INTEREST_INCOME": 1200.0, "REVENUE": 2000.0, "OPERATING_EXPENSE": 800.0,
                "CREDIT_LOSS_PROVISION": 200.0, "LOANS": 18000.0,
                "OPERATING_CASH_FLOW": 5000.0, "CAPEX": -50.0,
            }),
            _bank_period(2025, {
                "NET_INCOME": 750.0, "EQUITY": 3600.0, "TOTAL_ASSETS": 36000.0,
                "NET_INTEREST_INCOME": 1500.0, "REVENUE": 2400.0, "OPERATING_EXPENSE": 900.0,
                "CREDIT_LOSS_PROVISION": 240.0, "LOANS": 21000.0,
                "OPERATING_CASH_FLOW": -3000.0, "CAPEX": -60.0,
            }),
        ]


@pytest.fixture
def finance_providers(fake_providers):
    fake_providers.company = FakeFinanceCompanyProvider()
    fake_providers.financial = FakeBankFinancialProvider()
    return fake_providers


async def _latest_context(db_session, ticker: str) -> StructuredAnalysisContext:
    result = await db_session.execute(
        select(AnalysisSnapshot).where(AnalysisSnapshot.ticker == ticker).order_by(AnalysisSnapshot.created_at.desc())
    )
    return StructuredAnalysisContext.model_validate(result.scalars().first().context_json)


@pytest.mark.asyncio
async def test_bank_refresh_uses_bank_engine(client, finance_providers, db_session):
    resp = await client.post("/api/companies/BNKA/refresh")
    assert resp.status_code == 200
    body = resp.json()

    assert body["unsupported_reason"] is None
    assert body["company"]["industry"] == "Bankacılık"  # taksonomi normalize etti

    bank = body["bank_metrics"]
    assert bank["roe"] == pytest.approx(750 / 3300)
    assert bank["nim_proxy"] == pytest.approx(1500 / 33000)
    assert bank["equity_to_assets"] == pytest.approx(0.1)
    assert bank["loan_to_deposit"] is None  # mevduat kalemi yok → tahmin edilmez
    assert "DEPOSITS" in bank["missing_fields"]

    scores = body["scores"]
    assert scores["engine_version"] == "bank-v1"
    assert body["versions"]["scoring_engine"] == "bank-v1"
    assert scores["overall_weights"]["cash_flow"] == 0.0
    assert 0 < scores["overall"] <= 100

    valuation = body["valuation"]
    assert valuation["dcf"] is None
    assert valuation["ev_ebitda"] is None
    assert valuation["pb"] == pytest.approx(5000 / 3600)
    assert valuation["pb_historical_median"] == pytest.approx(4000 / 3000)

    assert body["metrics"]["ebitda_margin"] is None
    assert body["metrics"]["roe"] == bank["roe"]
    assert all(p["free_cash_flow"] is None for p in body["financial_history"])

    lenses = {lens["key"]: lens for lens in body["verdict"]["lenses"]}
    assert lenses["dcf"]["verdict"] is None
    assert lenses["dcf"]["not_applicable"] is True
    assert lenses["dcf"]["reason"] == BANK_DCF_NOT_APPLICABLE_MESSAGE
    assert lenses["history"]["verdict"] == "MAKUL"
    assert "verdict_lens_dcf" not in body["verdict"]["missing_fields"]
    assert body["verdict"]["quality"] is not None

    assert not any("temel" in w for w in body["data_quality"]["warnings"])
    assert body["data_quality"]["completeness"] == 1.0

    # Snapshot'tan okunduğunda aynı banka göstergeleri döner (ADR-005).
    cached = (await client.get("/api/companies/BNKA/analysis")).json()
    assert cached["bank_metrics"] == bank

    # Banka göstergeleri LLM prompt'una Türkçe biçimde girer.
    prompt_ctx = format_context_for_prompt(await _latest_context(db_session, "BNKA"))
    assert prompt_ctx["bank_metrics"]["equity_to_assets"] == "%10,0"
    assert "DCF bankalara uygulanmaz" in prompt_ctx["bank_metrics"]["note"]


@pytest.mark.asyncio
async def test_bank_dcf_endpoint_refuses(client, finance_providers):
    await client.post("/api/companies/BNKA/refresh")
    resp = await client.get("/api/companies/BNKA/analysis/dcf")
    assert resp.status_code == 422
    assert resp.json()["detail"] == BANK_DCF_NOT_APPLICABLE_MESSAGE


@pytest.mark.asyncio
async def test_insurer_is_still_unsupported(client, finance_providers):
    body = (await client.post("/api/companies/SGRA/refresh")).json()
    assert body["unsupported_reason"] == UNSUPPORTED_INDUSTRY_MESSAGE
    assert body["bank_metrics"] is None
    assert body["scores"]["unsupported_reason"] == UNSUPPORTED_INDUSTRY_MESSAGE
    assert body["verdict"]["unsupported_reason"] == UNSUPPORTED_INDUSTRY_MESSAGE
    assert body["versions"]["scoring_engine"] == "v1"


@pytest.mark.asyncio
async def test_generic_company_prompt_has_no_bank_section(client, finance_providers, db_session):
    finance_providers.financial = FakeBankFinancialProvider()  # tablo önemli değil
    body = (await client.post("/api/companies/SANAYI/refresh")).json()
    assert body["bank_metrics"] is None
    assert body["versions"]["scoring_engine"] == "v1"
    prompt_ctx = format_context_for_prompt(await _latest_context(db_session, "SANAYI"))
    assert "bank_metrics" not in prompt_ctx


@pytest.mark.asyncio
async def test_bank_peer_lens_compares_with_banks_only(client, finance_providers):
    await client.post("/api/companies/SGRA/refresh")
    await client.post("/api/companies/SGRB/refresh")
    first = (await client.post("/api/companies/BNKA/refresh")).json()
    peers_first = next(lens for lens in first["verdict"]["lenses"] if lens["key"] == "peers")
    assert peers_first["verdict"] is None
    assert "(0)" in peers_first["reason"]  # sigortacılar sayılmaz

    await client.post("/api/companies/BNKB/refresh")
    third = (await client.post("/api/companies/BNKC/refresh")).json()
    peers_third = next(lens for lens in third["verdict"]["lenses"] if lens["key"] == "peers")
    assert peers_third["verdict"] is not None
    assert "2+ benzer şirket" in peers_third["reason"]


@pytest.mark.asyncio
async def test_bank_skips_generic_quality_flags_but_gets_history_labels(client, finance_providers):
    # Birleştirme sonrası etkileşim: genel kalite kuralları (FAVÖK marjı,
    # hasılat/nakit akışı) bankaya uygulanmamalı; değerleme etiketleri ise
    # bankada da hüküm eşikleriyle üretilmeli.
    body = (await client.post("/api/companies/BNKA/refresh")).json()

    assert body["quality_flags"]["flags"] == []
    assert body["quality_flags"]["missing_fields"] == ["not_applicable_bank"]
    assert "bankalar için uygulanmaz" in body["quality_flags"]["not_applicable_reason"]
    # Banka "desteklenmeyen sektör" değildir; reel büyüme yine denenir
    # (burada TÜFE sahte olduğu için hesaplanmaz, tahmin de edilmez).
    assert "unsupported_industry" not in body["real_growth"]["missing_fields"]
    assert body["versions"]["financial_engine"] == "bank-v1"

    valuation = body["valuation"]
    assert valuation["pb_vs_history_ratio"] is not None
    assert valuation["pb_vs_history_label"] in {"UCUZ", "MAKUL", "PAHALI"}
    assert valuation["ev_ebitda_vs_history_label"] is None  # bankada FD/FAVÖK yok
