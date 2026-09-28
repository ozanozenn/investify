from __future__ import annotations

import datetime as dt

from app.llm.context_formatter import format_context_for_prompt
from app.schemas.context import (
    CompanyContext,
    DataQuality,
    MacroSeriesPoint,
    MarketContext,
    StructuredAnalysisContext,
)
from app.schemas.financial import FinancialMetrics
from app.schemas.scoring import CategoryScore, ScoreResult
from app.schemas.valuation import ValuationMetrics


def _context(**overrides) -> StructuredAnalysisContext:
    empty_category = CategoryScore(label="x", score=50.0, components=[])
    defaults = dict(
        ticker="ASELS",
        as_of=dt.datetime.now(dt.timezone.utc),
        company=CompanyContext(ticker="ASELS", name="Aselsan A.Ş.", sector=None, industry=None),
        market=MarketContext(price=125.4, currency="TRY", market_cap=1_000_000_000.0, as_of=None),
        metrics=FinancialMetrics(
            as_of_period="2025",
            ebitda_growth_yoy=0.8259859533087344,
            net_debt_to_ebitda=0.3660435829137801,
            free_cash_flow=-10733502000.0,
        ),
        financial_history=[],
        valuation=ValuationMetrics(pe=56.67737461756061),
        scores=ScoreResult(
            growth=empty_category,
            profitability=empty_category,
            balance_sheet=empty_category,
            cash_flow=empty_category,
            valuation=empty_category,
            overall=66.5,
            overall_weights={"growth": 0.25},
            engine_version="v1",
        ),
        macro=[
            MacroSeriesPoint(
                code="policy_rate", label="TCMB Politika Faizi", value=37.0,
                observation_date=dt.date.today(), is_mock=False,
            ),
            MacroSeriesPoint(
                code="usdtry", label="USD/TRY", value=41.23,
                observation_date=dt.date.today(), is_mock=False,
            ),
        ],
        disclosures=[],
        data_quality=DataQuality(completeness=1.0, freshness=1.0, metric_coverage=1.0, overall=1.0),
        sources=[],
    )
    defaults.update(overrides)
    return StructuredAnalysisContext(**defaults)


def test_ratio_field_is_formatted_as_percent():
    formatted = format_context_for_prompt(_context())
    assert formatted["metrics"]["ebitda_growth_yoy"] == "%82,6"


def test_multiple_field_is_formatted_with_x_suffix():
    formatted = format_context_for_prompt(_context())
    assert formatted["metrics"]["net_debt_to_ebitda"] == "0,4x"
    assert formatted["valuation"]["pe"] == "56,7x"


def test_negative_currency_field_keeps_sign():
    formatted = format_context_for_prompt(_context())
    assert formatted["metrics"]["free_cash_flow"] == "-10,7 milyar TL"


def test_score_field_is_formatted_with_denominator():
    formatted = format_context_for_prompt(_context())
    assert formatted["scores"]["overall"] == "66,5/100"


def test_macro_percent_point_vs_fx_rate_use_different_styles():
    formatted = format_context_for_prompt(_context())
    macro_by_code = {m["code"]: m["value"] for m in formatted["macro"]}
    assert macro_by_code["policy_rate"] == "%37,0"
    assert macro_by_code["usdtry"] == "41,23 TL"


def test_missing_optional_field_stays_none():
    formatted = format_context_for_prompt(_context())
    assert formatted["metrics"]["roe"] is None
    assert formatted["valuation"]["dcf"] is None


def test_next_rate_decision_date_is_formatted_in_turkish():
    context = _context(next_rate_decision_date=dt.date(2026, 10, 22))
    formatted = format_context_for_prompt(context)
    assert formatted["next_rate_decision_date"] == "22 Ekim 2026"


def test_next_rate_decision_date_absent_stays_none():
    formatted = format_context_for_prompt(_context())
    assert formatted["next_rate_decision_date"] is None
