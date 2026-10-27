"""Live-verified 2026-09-17 against real Gemini output: Turkish-language
disclosure titles containing dates ("16-09-2026") and ordinals ("2.
Çeyrek") produced false-positive hallucination flags before the fixes
this file tests for (see hallucination_guard.py's module comments)."""

from __future__ import annotations

import datetime as dt

from app.llm.hallucination_guard import find_unsupported_numbers
from app.schemas.context import (
    CompanyContext,
    DataQuality,
    MacroSeriesPoint,
    MarketContext,
    StructuredAnalysisContext,
)
from app.schemas.financial import FinancialMetrics
from app.schemas.llm_analysis import HorizonOutlook, LLMAnalysisResult
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
    empty_horizon = HorizonOutlook(outlook="NEUTRAL", rationale="Gerekçe.")
    return LLMAnalysisResult(
        executive_summary=text,
        what_matters_now=[],
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


def test_grouped_thousands_number_is_read_as_one_token_not_fragments():
    # Real bug found 2026-09-28: the old regex split a large Turkish-
    # formatted TRY amount at each thousands separator, so it never
    # actually checked the real number against the context.
    context = _context()
    context.metrics.free_cash_flow = 10733502000.0
    text = "Serbest nakit akışı 10.733.502.000 TL seviyesindedir."
    flags = find_unsupported_numbers(context, _result(text))
    assert flags == []


def test_sign_flip_on_grouped_number_is_flagged():
    # The actual LLM hallucination this guard is meant to catch: a
    # correct-magnitude number with the wrong sign.
    context = _context()
    context.metrics.free_cash_flow = 10733502000.0
    text = "Serbest nakit akışı -10.733.502.000 TL seviyesindedir."
    flags = find_unsupported_numbers(context, _result(text))
    assert len(flags) == 1
    assert "10.733.502.000" in flags[0]


def test_percent_formatted_ratio_field_is_verified_against_context():
    context = _context()  # ebitda_margin=0.264
    text = "FAVÖK marjı %26,4 seviyesinde gerçekleşmiştir."
    flags = find_unsupported_numbers(context, _result(text))
    assert flags == []


def test_turkish_month_name_date_in_prose_is_not_flagged():
    # Real bug found live 2026-09-28: company-analysis-v3 asks the LLM to
    # write in natural Turkish, which spells out dates like "23 Eylül 2026"
    # instead of "23-09-2026" — the bare day-of-month digit was flagged.
    text = "23 Eylül 2026 tarihli KAP bildiriminde belirtilen sözleşme imzalanmıştır."
    flags = find_unsupported_numbers(_context(), _result(text))
    assert flags == []


def test_percent_points_macro_value_is_verified_against_context():
    context = _context()
    context.macro = [
        MacroSeriesPoint(code="policy_rate", label="TCMB Politika Faizi", value=37.0,
                          observation_date=dt.date.today(), is_mock=False)
    ]
    text = "TCMB politika faizi %37,0 seviyesindedir."
    flags = find_unsupported_numbers(context, _result(text))
    assert flags == []


# --- company-analysis-v4 -----------------------------------------------------


def _verdict() -> Verdict:
    return Verdict(
        price="PAHALI",
        quality="ORTA",
        confidence="ORTA",
        headline="Orta kalitede şirket, fiyatı pahalı — 3 değerleme yönteminden 2 tanesi bu yönde.",
        lenses=[
            VerdictLens(key="history", label="Kendi geçmişine göre", verdict="PAHALI", value=1.12,
                        reason="Çarpanları son 5 yıllık medyanının %12 üstünde."),
            VerdictLens(key="dcf", label="İndirgenmiş nakit akışına (DCF) göre", verdict="PAHALI", value=-0.31,
                        reason="Baz senaryo içsel değeri güncel fiyatın %31 altında."),
        ],
        agreement=0.6667,
        overall_score=57.5,
        engine_version="v1",
    )


def test_v4_what_matters_now_and_horizon_rationale_are_checked():
    result = _result("Temiz özet.")
    result.what_matters_now = ["Net kâr marjı 42.7 seviyesinde."]
    result.medium_term = HorizonOutlook(outlook="NEUTRAL", rationale="Büyüme %88,8 olabilir.")
    flags = find_unsupported_numbers(_context(), result)
    assert len(flags) == 2
    assert any("42.7" in f for f in flags)
    assert any("88,8" in f for f in flags)


def test_numbers_from_verdict_text_given_to_llm_are_supported():
    context = _context()
    context.verdict = _verdict()
    text = (
        "Hüküm: 3 değerleme yönteminden 2 tanesi pahalı diyor; çarpanlar son 5 yılın "
        "%12 üstünde ve DCF içsel değeri fiyatın %31 altında."
    )
    assert find_unsupported_numbers(context, _result(text)) == []


def test_verdict_numbers_are_not_supported_without_a_verdict():
    # Same text, no verdict in context -> those numbers have no source.
    text = "DCF içsel değeri fiyatın %31 altında."
    assert len(find_unsupported_numbers(_context(), _result(text))) == 1


def test_raw_verdict_ratios_not_sent_to_llm_are_not_supported():
    # lens.value=1.12 never reaches the prompt (only the reason text does).
    context = _context()
    context.verdict = _verdict()
    flags = find_unsupported_numbers(context, _result("Çarpan oranı 1,12 kat."))
    assert len(flags) == 1
