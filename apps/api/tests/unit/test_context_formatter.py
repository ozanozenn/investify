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
from app.schemas.verdict import Verdict, VerdictLens


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


def _verdict(signal: str | None = "TUT") -> Verdict:
    return Verdict(
        price="PAHALI",
        quality="GUCLU",
        confidence="ORTA",
        signal=signal,
        headline="Güçlü şirket, fiyatı pahalı — 2 değerleme yönteminden 2 tanesi bu yönde.",
        lenses=[
            VerdictLens(key="history", label="Kendi geçmişine göre", verdict="PAHALI", value=1.12,
                        reason="Çarpanları son 5 yıllık medyanının %12 üstünde."),
            VerdictLens(key="peers", label="Sektörüne göre", verdict=None, value=None,
                        reason="Karşılaştırılacak yeterli benzer şirket yok (0)."),
        ],
        agreement=1.0,
        overall_score=66.5,
        engine_version="v1",
        missing_fields=["verdict_lens_peers"],
    )


def test_verdict_is_sent_with_turkish_labels_and_engine_reasons():
    formatted = format_context_for_prompt(_context(verdict=_verdict()))
    v = formatted["verdict"]
    assert v["headline"].startswith("Güçlü şirket, fiyatı pahalı")
    assert (v["price"], v["quality"], v["confidence"]) == ("Pahalı", "Güçlü", "Orta")
    assert v["lenses"][0] == {
        "label": "Kendi geçmişine göre",
        "verdict": "Pahalı",
        "reason": "Çarpanları son 5 yıllık medyanının %12 üstünde.",
    }
    assert v["lenses"][1]["verdict"] is None
    assert v["missing_fields"] == ["verdict_lens_peers"]


def test_verdict_raw_ratios_are_not_sent_to_llm():
    v = format_context_for_prompt(_context(verdict=_verdict()))["verdict"]
    assert "agreement" not in v and "overall_score" not in v
    assert all("value" not in lens for lens in v["lenses"])


def test_verdict_signal_is_sent_only_as_labeled_demo():
    v = format_context_for_prompt(_context(verdict=_verdict()))["verdict"]
    assert v["demo_signal"].startswith("TUT (")
    assert "demo" in v["demo_signal"] and "tavsiyesi değildir" in v["demo_signal"]
    assert "signal" not in v

    no_signal = format_context_for_prompt(_context(verdict=_verdict(signal=None)))["verdict"]
    assert no_signal["demo_signal"] is None


def test_old_snapshot_without_verdict_formats_as_none():
    assert format_context_for_prompt(_context())["verdict"] is None
