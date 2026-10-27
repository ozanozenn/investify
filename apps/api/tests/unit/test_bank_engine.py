"""Banka motoru, tespiti, skoru ve LLM context biçimi (ADR-014)."""

from __future__ import annotations

import datetime as dt

import pytest

from app.financial_engine.bank_engine import (
    BANK_ENGINE_VERSION,
    COST_INCOME_APPROXIMATION,
    NII_DERIVED,
    NO_PREVIOUS_PERIOD,
    compute_bank_metrics,
)
from app.financial_engine.industry_strategy import is_bank_industry
from app.llm.bank_context_formatter import format_bank_metrics
from app.providers.base import Candle, Quote
from app.schemas.financial import PeriodData
from app.scoring_engine.bank_scoring import compute_bank_score, get_bank_scoring_config
from app.services.bank_analysis import (
    DCF_NOT_APPLICABLE,
    EV_EBITDA_NOT_APPLICABLE,
    GENERIC_METRICS_NOT_APPLICABLE,
    analyze_bank,
)
from app.services.data_quality import compute_bank_data_quality


def _period(year: int, **values: float) -> PeriodData:
    return PeriodData(
        period_type="ANNUAL", fiscal_year=year, period_end_date=dt.date(year, 12, 31), values=values
    )


# Banka benzeri iki yıl (milyon TL ölçeğinde yuvarlak sayılar).
PREV = _period(
    2024,
    NET_INCOME=80.0, EQUITY=400.0, TOTAL_ASSETS=4000.0, NET_INTEREST_INCOME=150.0,
)
LATEST = _period(
    2025,
    NET_INCOME=100.0, EQUITY=500.0, TOTAL_ASSETS=5000.0, NET_INTEREST_INCOME=180.0,
    OPERATING_EXPENSE=-90.0, REVENUE=300.0, CREDIT_LOSS_PROVISION=36.0,
    LOANS=3000.0, DEPOSITS=3750.0,
)


def test_bank_metrics_normal_case():
    m = compute_bank_metrics([LATEST, PREV])  # sıra önemli değil

    assert m.as_of_period == "2025"
    assert m.engine_version == BANK_ENGINE_VERSION
    assert m.roe == pytest.approx(100 / 450)
    assert m.roa == pytest.approx(100 / 4500)
    assert m.nim_proxy == pytest.approx(180 / 4500)
    assert m.nii_growth_yoy == pytest.approx(0.2)
    assert m.net_income_growth_yoy == pytest.approx(0.25)
    assert m.equity_growth_yoy == pytest.approx(0.25)
    assert m.equity_to_assets == pytest.approx(0.1)
    assert m.loan_to_deposit == pytest.approx(0.8)
    assert m.provision_to_nii == pytest.approx(0.2)
    # Gider işareti sağlayıcıya göre değişir; mutlak değer kullanılır.
    assert m.cost_income_ratio == pytest.approx(0.3)
    assert m.latest_net_interest_income == 180.0
    assert m.latest_deposits == 3750.0
    # Hiçbir girdi eksik değil; yalnızca yaklaşıklık işareti var.
    assert m.missing_fields == [COST_INCOME_APPROXIMATION]


def test_bank_metrics_missing_fields_are_never_guessed():
    only_profit = _period(2025, NET_INCOME=100.0, EQUITY=500.0)
    m = compute_bank_metrics([only_profit])

    assert m.roe == pytest.approx(0.2)  # tek dönem: o dönemin özkaynağı
    assert m.roa is None
    assert m.nim_proxy is None
    assert m.equity_to_assets is None
    assert m.loan_to_deposit is None
    assert m.provision_to_nii is None
    assert m.cost_income_ratio is None
    assert m.nii_growth_yoy is None
    assert m.net_income_growth_yoy is None
    for field in ("TOTAL_ASSETS", "NET_INTEREST_INCOME", "OPERATING_EXPENSE", "REVENUE",
                  "CREDIT_LOSS_PROVISION", "LOANS", "DEPOSITS", NO_PREVIOUS_PERIOD):
        assert field in m.missing_fields
    assert "NET_INCOME" not in m.missing_fields
    assert COST_INCOME_APPROXIMATION not in m.missing_fields


def test_no_periods_returns_empty_metrics():
    m = compute_bank_metrics([])
    assert m.as_of_period == "N/A"
    assert m.missing_fields == ["no_financial_periods"]
    assert m.roe is None


def test_nii_derived_from_interest_income_and_expense_is_flagged():
    p = _period(2025, NET_INCOME=10.0, EQUITY=50.0, TOTAL_ASSETS=500.0,
                INTEREST_INCOME=120.0, INTEREST_EXPENSE=80.0)
    m = compute_bank_metrics([p])
    assert m.latest_net_interest_income == 40.0
    assert NII_DERIVED in m.missing_fields
    assert "NET_INTEREST_INCOME" not in m.missing_fields


def test_non_positive_nii_gives_no_provision_ratio():
    p = _period(2025, NET_INCOME=-5.0, EQUITY=50.0, TOTAL_ASSETS=500.0,
                NET_INTEREST_INCOME=-1.0, CREDIT_LOSS_PROVISION=3.0)
    assert compute_bank_metrics([p]).provision_to_nii is None


@pytest.mark.parametrize(
    ("is_financial", "industry", "expected"),
    [
        (True, "Bankacılık", True),
        (True, "BANKACILIK", True),
        (True, "Banks - Regional", True),
        (True, "Banks—Diversified", True),
        (True, "Sigorta", False),
        (True, "GYO", False),
        (True, "Capital Markets", False),
        (True, None, False),
        (False, "Bankacılık", False),
    ],
)
def test_is_bank_industry(is_financial, industry, expected):
    assert is_bank_industry(is_financial, industry) is expected


def test_bank_score_excludes_cash_flow_explicitly():
    cfg = get_bank_scoring_config()
    weights = cfg["overall_weights"]
    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights["cash_flow"] == 0.0
    assert len(cfg["version"]) <= 10  # DB sütunu String(10)

    m = compute_bank_metrics([LATEST, PREV])
    scores = compute_bank_score({**m.model_dump(), "pe_vs_history_ratio": 1.0, "pb_vs_history_ratio": 1.0})

    assert scores.engine_version == "bank-v1"
    assert scores.cash_flow.score == 0.0
    assert scores.cash_flow.components[0].max_points == 0.0
    assert "bankalarda uygulanmaz" in scores.cash_flow.label
    expected = sum(getattr(scores, k).score * w for k, w in weights.items() if k != "cash_flow")
    assert scores.overall == pytest.approx(round(expected, 1))
    assert 0 < scores.overall <= 100


def test_bank_score_missing_component_rescales_not_zero():
    m = compute_bank_metrics([LATEST, PREV])
    full = compute_bank_score(m.model_dump())
    without_ldr = compute_bank_score({**m.model_dump(), "loan_to_deposit": None})
    ldr = next(c for c in without_ldr.balance_sheet.components if c.metric == "loan_to_deposit")
    assert ldr.value is None
    assert "hariç tutuldu" in ldr.reason
    assert without_ldr.balance_sheet.score > 0
    assert full.profitability.score == without_ldr.profitability.score


def _quote() -> Quote:
    now = dt.datetime.now(dt.timezone.utc)
    return Quote(
        ticker="BANKA", price=10.0, currency="TRY", market_cap=600.0, shares_outstanding=60.0,
        fifty_two_week_high=None, fifty_two_week_low=None, as_of=now, source_code="test", fetched_at=now,
    )


def test_analyze_bank_uses_pe_pb_only_and_no_dcf():
    with_debt = LATEST.model_copy(update={"values": {**LATEST.values, "TOTAL_DEBT": 900.0, "CASH": 100.0, "EBITDA": 150.0}})
    candles = [Candle(date=dt.date(2024, 12, 31), open=7, high=8, low=7, close=8.0, volume=1)]
    result = analyze_bank([PREV, with_debt], _quote(), candles, lookback_years=5)

    v = result.valuation
    assert v.pb == pytest.approx(600 / 500)
    assert v.pe == pytest.approx(600 / 100)
    assert v.pb_historical_median == pytest.approx(8.0 * 60 / 400)
    # FD/FAVÖK bankada anlamsız: veri olsa bile boşaltılır; DCF yok.
    assert v.ev_ebitda is None and v.ev_ebitda_vs_history_ratio is None
    assert v.dcf is None
    assert EV_EBITDA_NOT_APPLICABLE in v.missing_fields
    assert DCF_NOT_APPLICABLE in v.missing_fields
    assert "ev_ebitda_unavailable" not in v.missing_fields

    assert result.scores.engine_version == "bank-v1"
    pb_comp = next(c for c in result.scores.valuation.components if c.metric == "pb_vs_history_ratio")
    assert pb_comp.value == pytest.approx(v.pb_vs_history_ratio)

    # Genel metrikler: yalnızca tanımı aynı olanlar dolu.
    assert result.metrics.roe == result.bank_metrics.roe
    assert result.metrics.ebitda_margin is None
    assert result.metrics.missing_fields == [GENERIC_METRICS_NOT_APPLICABLE]


def test_bank_data_quality_counts_bank_core_fields_only():
    m = compute_bank_metrics([LATEST, PREV])
    dq = compute_bank_data_quality(m, {"market": "SUCCESS", "financials": "SUCCESS"}, market_available=True)
    assert dq.completeness == 1.0
    assert dq.metric_coverage == 1.0
    assert dq.overall == 1.0
    assert dq.warnings == []

    empty = compute_bank_data_quality(
        compute_bank_metrics([]), {"financials": "FAILED"}, market_available=True
    )
    assert empty.completeness == 0.0
    assert any("temel banka finansal alanı eksik" in w for w in empty.warnings)


def test_bank_metrics_formatted_for_llm_in_turkish_style():
    out = format_bank_metrics(compute_bank_metrics([LATEST, PREV]))
    assert out["roe"] == "%22,2"
    assert out["equity_to_assets"] == "%10,0"
    assert out["latest_net_income"] == "100,00 TL"
    assert "DCF bankalara uygulanmaz" in out["note"]
    assert "yaklaşık" in out["note"]
