"""Live-verified 2026-09-17 against real Gemini output: Turkish-language
disclosure titles containing dates ("16-09-2026") and ordinals ("2.
Çeyrek") produced false-positive hallucination flags before the fixes
this file tests for (see hallucination_guard.py's module comments)."""

from __future__ import annotations

import datetime as dt

from app.llm.hallucination_guard import find_unsupported_numbers
from app.schemas.context import CompanyContext, DataQuality, MarketContext, StructuredAnalysisContext
from app.schemas.financial import FinancialMetrics
from app.schemas.llm_analysis import HorizonOutlook, LLMAnalysisResult
from app.schemas.scoring import CategoryScore, ScoreResult
from app.schemas.valuation import ValuationMetrics


def _context() -> StructuredAnalysisContext:
    empty_category = CategoryScore(label="x", score=50.0, components=[])
    return StructuredAnalysisContext(
        ticker="TEST",
        as_of=dt.datetime.now(dt.timezone.utc),
        company=CompanyContext(ticker="TEST", name="Test A.Ş.", sector=None, industry=None),
        market=MarketContext(price=10.0, currency="TRY", market_cap=1000.0, as_of=None),
        metrics=FinancialMetrics(as_of_period="2025", ebitda_margin=0.264),
        financial_history=[],
        valuation=ValuationMetrics(),
        scores=ScoreResult(
            growth=empty_category,
            profitability=empty_category,
            balance_sheet=empty_category,
            cash_flow=empty_category,
            valuation=empty_category,
            overall=57.5,
            overall_weights={},
            engine_version="v1",
        ),
        macro=[],
        disclosures=[],
        data_quality=DataQuality(completeness=1.0, freshness=1.0, metric_coverage=1.0, overall=1.0),
        sources=[],
    )


def _result(text: str) -> LLMAnalysisResult:
    empty_horizon = HorizonOutlook(outlook="NEUTRAL", confidence=0.5, drivers=[], risks=[], catalysts=[])
    return LLMAnalysisResult(
        executive_summary=text,
        short_term=empty_horizon,
        medium_term=empty_horizon,
        long_term=empty_horizon,
        bull_case=[],
        bear_case=[],
        key_risks=[],
        key_catalysts=[],
        thesis_breakers=[],
        what_to_watch=[],
    )


def test_date_inside_quoted_disclosure_title_is_not_flagged():
    text = "16-09-2026 tarihinde hissede uygulanan Pay Bazında Devre Kesici süreci devreye girmiştir."
    flags = find_unsupported_numbers(_context(), _result(text))
    assert flags == []


def test_iso_style_date_is_not_flagged():
    text = "Şirket 2026-09-16 tarihli açıklamasında üretim kapasitesini artıracağını duyurdu."
    flags = find_unsupported_numbers(_context(), _result(text))
    assert flags == []


def test_turkish_ordinal_quarter_is_not_flagged():
    text = "2026 2. Çeyrek Finansal Sonuçlar gibi çeyreklik bilanço dönemi verileri takip edilmeli."
    flags = find_unsupported_numbers(_context(), _result(text))
    assert flags == []


def test_real_context_number_still_passes():
    text = "FAVÖK marjı 0.264 seviyesinde yüksek kalmaya devam etmektedir."
    flags = find_unsupported_numbers(_context(), _result(text))
    assert flags == []


def test_genuinely_unverifiable_number_is_still_flagged():
    text = "Şirketin net kâr marjı 42.7 seviyesine ulaşmıştır."
    flags = find_unsupported_numbers(_context(), _result(text))
    assert len(flags) == 1
    assert "42.7" in flags[0]
