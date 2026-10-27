"""company-analysis-v4 çıktı şeması: madde sınırları ve mock'un v4 şekli."""

from __future__ import annotations

import datetime as dt

import pytest

from app.llm.mock_provider import MockLLMProvider
from app.schemas.context import CompanyContext, DataQuality, MarketContext, StructuredAnalysisContext
from app.schemas.financial import FinancialMetrics
from app.schemas.llm_analysis import MAX_ITEMS, LLMAnalysisResult
from app.schemas.scoring import CategoryScore, ScoreResult
from app.schemas.valuation import ValuationMetrics
from app.schemas.verdict import Verdict, VerdictLens


def _context() -> StructuredAnalysisContext:
    empty_category = CategoryScore(label="x", score=50.0, components=[])
    return StructuredAnalysisContext(
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


def _payload(**lists: list[str]) -> dict:
    horizon = {"outlook": "NEUTRAL", "rationale": "Gerekçe."}
    base = {name: [] for name in MAX_ITEMS}
    base.update(lists)
    return {"executive_summary": "Özet.", "short_term": horizon, "medium_term": horizon, "long_term": horizon, **base}


def test_over_long_lists_are_trimmed_to_the_v4_limits_keeping_the_first_items():
    too_many = [f"madde {i}" for i in range(10)]
    result = LLMAnalysisResult.model_validate(_payload(**{name: too_many for name in MAX_ITEMS}))
    for name, limit in MAX_ITEMS.items():
        assert getattr(result, name) == too_many[:limit]


def test_limits_match_the_v4_prompt_contract():
    assert MAX_ITEMS == {
        "what_matters_now": 5,
        "bull_case": 3,
        "bear_case": 3,
        "key_risks": 4,
        "key_catalysts": 4,
        "thesis_breakers": 3,
        "what_to_watch": 4,
    }


def test_outlook_must_be_one_of_the_enum_values():
    payload = _payload()
    payload["short_term"] = {"outlook": "BULLISH", "rationale": "x"}
    with pytest.raises(ValueError):
        LLMAnalysisResult.model_validate(payload)


@pytest.mark.asyncio
async def test_mock_explains_verdict_in_v4_shape():
    context = _context()
    context.verdict = Verdict(
        price="PAHALI", quality="ORTA", confidence="ORTA",
        headline="Orta kalitede şirket, fiyatı pahalı — 1 değerleme yönteminden 1 tanesi bu yönde.",
        lenses=[
            VerdictLens(key="dcf", label="İndirgenmiş nakit akışına (DCF) göre", verdict="PAHALI", value=-0.31,
                        reason="Baz senaryo içsel değeri güncel fiyatın %31 altında."),
            VerdictLens(key="peers", label="Sektörüne göre", verdict=None, value=None,
                        reason="Karşılaştırılacak yeterli benzer şirket yok (0)."),
        ],
        agreement=1.0, overall_score=57.5, engine_version="v1",
    )
    result = await MockLLMProvider().analyze_company(context, "company-analysis-v4", extra_instructions="yok sayılır")
    assert context.verdict.headline in result.executive_summary
    # Only lenses that actually voted are echoed.
    assert result.what_matters_now == [
        "İndirgenmiş nakit akışına (DCF) göre: Baz senaryo içsel değeri güncel fiyatın %31 altında."
    ]
    assert result.short_term.rationale
