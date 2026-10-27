"""Kalite bayrakları / reel büyüme LLM context'ine Türkçe biçimli girer,
eski snapshot'lar bozulmaz ve halüsinasyon koruması bu sayıları tanır
(ADR-016, ADR-003)."""

from __future__ import annotations

import datetime as dt

from app.llm.context_formatter import format_context_for_prompt
from app.llm.hallucination_guard import find_unsupported_numbers
from app.schemas.context import CompanyContext, DataQuality, MarketContext, StructuredAnalysisContext
from app.schemas.financial import FinancialMetrics
from app.schemas.llm_analysis import HorizonOutlook, LLMAnalysisResult
from app.schemas.quality import QualityFlag, QualityFlagsResult, QualityFlagValue, RealGrowth, UnevaluatedQualityCheck
from app.schemas.scoring import CategoryScore, ScoreResult
from app.schemas.valuation import ValuationMetrics


def _quality() -> QualityFlagsResult:
    return QualityFlagsResult(
        as_of_period="2025",
        flags=[
            QualityFlag(
                key="revenue_vs_cash",
                severity="UYARI",
                title="Gelir artıyor ama nakit akışı bozuluyor",
                detail="Satışlar artarken nakit azaldı.",
                values=[
                    QualityFlagValue(key="revenue_growth_yoy", label="Gelir büyümesi (yıllık)", value=0.4123, unit="ratio"),
                    QualityFlagValue(key="free_cash_flow_2025", label="Serbest nakit akışı (2025)", value=-2_345_000_000.0, unit="currency"),
                ],
            )
        ],
        passed_checks=["FAVÖK marjı eğilimi"],
        not_evaluated=[
            UnevaluatedQualityCheck(
                key="receivables_vs_revenue",
                name="Ticari alacaklar ile gelir büyümesi",
                reason="Gerekli veri eksik: Ticari alacaklar.",
                missing_fields=["RECEIVABLES"],
            )
        ],
        missing_fields=["RECEIVABLES"],
    )


def _real_growth() -> RealGrowth:
    return RealGrowth(
        as_of_period="2025",
        cpi_yoy=0.335,
        cpi_observation_date=dt.date(2026, 1, 1),
        revenue_growth_nominal=0.4123,
        revenue_growth_real=0.0579,
        net_income_growth_nominal=None,
        net_income_growth_real=None,
        missing_fields=["NET_INCOME"],
    )


def _context(**overrides) -> StructuredAnalysisContext:
    empty_category = CategoryScore(label="x", score=50.0, components=[])
    defaults = dict(
        ticker="TEST",
        as_of=dt.datetime.now(dt.timezone.utc),
        company=CompanyContext(ticker="TEST", name="Test A.Ş.", sector=None, industry=None),
        market=MarketContext(price=10.0, currency="TRY", market_cap=1000.0, as_of=None),
        metrics=FinancialMetrics(as_of_period="2025"),
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
    defaults.update(overrides)
    return StructuredAnalysisContext(**defaults)


def _result(text: str) -> LLMAnalysisResult:
    empty = HorizonOutlook(outlook="NEUTRAL", confidence=0.5, drivers=[], risks=[], catalysts=[])
    return LLMAnalysisResult(
        executive_summary=text,
        short_term=empty,
        medium_term=empty,
        long_term=empty,
        bull_case=[],
        bear_case=[],
        key_risks=[],
        key_catalysts=[],
        thesis_breakers=[],
        what_to_watch=[],
    )


def test_quality_flags_are_formatted_in_turkish():
    formatted = format_context_for_prompt(_context(quality_flags=_quality()))
    qf = formatted["quality_flags"]
    flag = qf["flags"][0]
    assert flag["severity"] == "UYARI"
    assert flag["values"] == {
        "Gelir büyümesi (yıllık)": "%41,2",
        "Serbest nakit akışı (2025)": "-2,3 milyar TL",
    }
    assert qf["not_evaluated"] == [
        {"name": "Ticari alacaklar ile gelir büyümesi", "reason": "Gerekli veri eksik: Ticari alacaklar."}
    ]
    assert qf["passed_checks"] == ["FAVÖK marjı eğilimi"]


def test_real_growth_is_formatted_with_approximation_note():
    formatted = format_context_for_prompt(_context(real_growth=_real_growth()))
    rg = formatted["real_growth"]
    assert rg["cpi_yoy"] == "%33,5"
    assert rg["cpi_observation_month"] == "Ocak 2026"
    assert rg["revenue_growth_nominal"] == "%41,2"
    assert rg["revenue_growth_real"] == "%5,8"
    assert rg["net_income_growth_real"] is None
    assert "Yaklaşık" in rg["note"]


def test_old_snapshot_without_quality_fields_still_parses_and_formats():
    raw = _context().model_dump(mode="json")
    raw.pop("quality_flags")
    raw.pop("real_growth")
    old = StructuredAnalysisContext.model_validate(raw)
    assert old.quality_flags is None and old.real_growth is None
    formatted = format_context_for_prompt(old)
    assert formatted["quality_flags"] is None
    assert formatted["real_growth"] is None


def test_hallucination_guard_accepts_quality_and_real_growth_numbers():
    ctx = _context(quality_flags=_quality(), real_growth=_real_growth())
    text = (
        "Gelir %41,2 artarken serbest nakit akışı -2,3 milyar TL oldu; "
        "%33,5 enflasyon düşüldüğünde reel büyüme %5,8 civarında."
    )
    assert find_unsupported_numbers(ctx, _result(text)) == []


def test_hallucination_guard_still_flags_invented_numbers():
    ctx = _context(quality_flags=_quality(), real_growth=_real_growth())
    flags = find_unsupported_numbers(ctx, _result("Reel büyüme %17,4 oldu."))
    assert len(flags) == 1
