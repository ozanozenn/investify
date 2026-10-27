"""Kalite bayrakları motoru (ADR-016): her kontrol için tetiklendi /
tetiklenmedi / veri eksik durumları. Eşikler gerçek
`config/quality_flags.yaml`'dan okunur; senaryolar eşiklerden bilinçli
olarak uzak seçildi."""

from __future__ import annotations

import datetime as dt
import re

import pytest

from app.financial_engine.quality_flags import compute_quality_flags
from app.schemas.financial import PeriodData
from app.services.quality_analysis import get_quality_flags_config

CONFIG = get_quality_flags_config()

# Sağlıklı şirket: her kalem ~%40 büyüyor, marjlar sabit, FCF pozitif.
_BASE_2024 = {
    "REVENUE": 1000.0,
    "EBITDA": 200.0,
    "NET_INCOME": 100.0,
    "EQUITY": 500.0,
    "TOTAL_DEBT": 300.0,
    "OPERATING_CASH_FLOW": 150.0,
    "CAPEX": -50.0,
    "RECEIVABLES": 200.0,
    "INVENTORY": 150.0,
}
_BASE_2025 = {
    "REVENUE": 1400.0,
    "EBITDA": 280.0,
    "NET_INCOME": 140.0,
    "EQUITY": 640.0,
    "TOTAL_DEBT": 400.0,
    "OPERATING_CASH_FLOW": 210.0,
    "CAPEX": -60.0,
    "RECEIVABLES": 280.0,
    "INVENTORY": 210.0,
}


def _period(year: int, values: dict[str, float]) -> PeriodData:
    return PeriodData(
        period_type="ANNUAL", fiscal_year=year, period_end_date=dt.date(year, 12, 31), values=values
    )


def _run(prev: dict | None = None, latest: dict | None = None, drop: tuple[str, ...] = ()):
    p24 = {**_BASE_2024, **(prev or {})}
    p25 = {**_BASE_2025, **(latest or {})}
    for key in drop:
        p24.pop(key, None)
        p25.pop(key, None)
    # Sıra önemsiz: motor kendisi sıralar.
    return compute_quality_flags([_period(2025, p25), _period(2024, p24)], CONFIG)


def _flag(result, key):
    return next((f for f in result.flags if f.key == key), None)


def _unevaluated(result, key):
    return next((c for c in result.not_evaluated if c.key == key), None)


def test_healthy_company_raises_no_flags_and_runs_every_check():
    result = _run()
    assert result.flags == []
    assert result.not_evaluated == []
    assert len(result.passed_checks) == 9
    assert result.as_of_period == "2025"
    assert result.engine_version == CONFIG["version"]
    assert result.missing_fields == []


def test_no_periods_is_reported_not_guessed():
    result = compute_quality_flags([], CONFIG)
    assert result.flags == []
    assert result.missing_fields == ["no_financial_periods"]


def test_single_period_cannot_compare_years():
    result = compute_quality_flags([_period(2025, dict(_BASE_2025))], CONFIG)
    assert result.flags == []
    assert _unevaluated(result, "revenue_vs_cash").missing_fields == ["previous_period"]
    assert "previous_period" in result.missing_fields


# --- Gelir artıyor ama nakit akışı bozuluyor ---------------------------------


def test_revenue_up_cash_down_triggers():
    result = _run(latest={"OPERATING_CASH_FLOW": 120.0})  # FNA -%20, gelir +%40
    flag = _flag(result, "revenue_vs_cash")
    assert flag is not None
    assert flag.severity == "UYARI"
    values = {v.key: v.value for v in flag.values}
    assert values["revenue_growth_yoy"] == pytest.approx(0.4)
    assert values["ocf_growth_yoy"] == pytest.approx(-0.2)


def test_revenue_up_small_cash_dip_does_not_trigger():
    result = _run(latest={"OPERATING_CASH_FLOW": 140.0})  # FNA -%6,7 > -%10
    assert _flag(result, "revenue_vs_cash") is None


def test_revenue_vs_cash_missing_ocf_is_not_evaluated():
    result = _run(drop=("OPERATING_CASH_FLOW",))
    check = _unevaluated(result, "revenue_vs_cash")
    assert check.missing_fields == ["OPERATING_CASH_FLOW"]
    assert "Faaliyet nakit akışı" in check.reason
    assert _flag(result, "revenue_vs_cash") is None


# --- Kâr nakitten hızlı büyüyor (tahakkuk kalitesi) -------------------------


def test_earnings_outpacing_cash_triggers():
    result = _run(latest={"NET_INCOME": 200.0})  # kâr +%100, FNA +%40
    flag = _flag(result, "earnings_vs_cash")
    assert flag is not None
    assert flag.severity == "DIKKAT"


def test_earnings_growing_with_cash_does_not_trigger():
    result = _run(latest={"NET_INCOME": 150.0})  # 1,5 / 1,4 - 1 = %7
    assert _flag(result, "earnings_vs_cash") is None


def test_earnings_up_while_ocf_turns_negative_triggers():
    result = _run(latest={"NET_INCOME": 150.0, "OPERATING_CASH_FLOW": -10.0})
    flag = _flag(result, "earnings_vs_cash")
    assert flag is not None
    assert "sıfırın altına" in flag.detail


def test_earnings_from_loss_base_is_not_evaluated():
    result = _run(prev={"NET_INCOME": -50.0})
    check = _unevaluated(result, "earnings_vs_cash")
    assert check.missing_fields == ["non_positive_base:NET_INCOME"]


# --- Marj daralması / genişlemesi --------------------------------------------


def test_ebitda_margin_contraction_triggers():
    result = _run(latest={"EBITDA": 224.0})  # %20 -> %16
    flag = _flag(result, "ebitda_margin_trend")
    assert flag is not None
    assert flag.severity == "DIKKAT"
    assert flag.title == "FAVÖK marjı daralıyor"
    values = {v.key: v.value for v in flag.values}
    assert values["ebitda_margin_trend_previous"] == pytest.approx(0.20)
    assert values["ebitda_margin_trend_latest"] == pytest.approx(0.16)


def test_ebitda_margin_expansion_is_positive_flag():
    result = _run(latest={"EBITDA": 350.0})  # %20 -> %25
    flag = _flag(result, "ebitda_margin_trend")
    assert flag.severity == "OLUMLU"


def test_small_margin_change_does_not_trigger():
    result = _run(latest={"EBITDA": 287.0})  # %20 -> %20,5
    assert _flag(result, "ebitda_margin_trend") is None


def test_net_margin_contraction_triggers():
    result = _run(latest={"NET_INCOME": 98.0})  # %10 -> %7
    flag = _flag(result, "net_margin_trend")
    assert flag is not None
    assert flag.severity == "DIKKAT"


def test_margin_missing_ebitda_is_not_evaluated():
    result = _run(drop=("EBITDA",))
    assert _unevaluated(result, "ebitda_margin_trend").missing_fields == ["EBITDA"]
    assert _unevaluated(result, "debt_vs_ebitda").missing_fields == ["EBITDA"]


# --- Borç FAVÖK'ten hızlı artıyor ---------------------------------------------


def test_debt_outpacing_ebitda_triggers():
    result = _run(latest={"TOTAL_DEBT": 600.0})  # borç +%100, FAVÖK +%40
    flag = _flag(result, "debt_vs_ebitda")
    assert flag is not None
    assert flag.severity == "UYARI"


def test_debt_growing_slower_than_ebitda_does_not_trigger():
    result = _run()  # borç +%33, FAVÖK +%40
    assert _flag(result, "debt_vs_ebitda") is None


def test_debt_up_while_ebitda_turns_negative_triggers():
    result = _run(latest={"EBITDA": -20.0})
    assert _flag(result, "debt_vs_ebitda") is not None


def test_debt_from_zero_base_is_not_evaluated():
    result = _run(prev={"TOTAL_DEBT": 0.0})
    assert _unevaluated(result, "debt_vs_ebitda").missing_fields == ["non_positive_base:TOTAL_DEBT"]


# --- Serbest nakit akışı art arda negatif -------------------------------------


def test_consecutive_negative_fcf_triggers():
    result = _run(
        prev={"OPERATING_CASH_FLOW": 40.0, "CAPEX": -50.0},  # FCF -10
        latest={"OPERATING_CASH_FLOW": 50.0, "CAPEX": -80.0},  # FCF -30
    )
    flag = _flag(result, "negative_fcf_streak")
    assert flag is not None
    assert flag.severity == "UYARI"
    assert [(v.key, v.value, v.unit) for v in flag.values] == [
        ("free_cash_flow_2024", -10.0, "currency"),
        ("free_cash_flow_2025", -30.0, "currency"),
    ]


def test_single_negative_fcf_year_does_not_trigger():
    result = _run(latest={"OPERATING_CASH_FLOW": 50.0, "CAPEX": -80.0})
    assert _flag(result, "negative_fcf_streak") is None


def test_explicit_provider_fcf_takes_precedence():
    result = _run(prev={"FREE_CASH_FLOW": -5.0}, latest={"FREE_CASH_FLOW": -7.0})
    assert _flag(result, "negative_fcf_streak") is not None


def test_fcf_streak_missing_capex_is_not_evaluated():
    result = _run(drop=("CAPEX",))
    assert _unevaluated(result, "negative_fcf_streak").missing_fields == ["FREE_CASH_FLOW"]


# --- Özkaynak eriyor -----------------------------------------------------------


def test_equity_shrinking_triggers():
    result = _run(latest={"EQUITY": 450.0})  # -%10
    flag = _flag(result, "equity_trend")
    assert flag.severity == "DIKKAT"
    assert flag.title == "Özkaynak eriyor"


def test_negative_equity_is_a_warning():
    result = _run(latest={"EQUITY": -20.0})
    flag = _flag(result, "equity_trend")
    assert flag.severity == "UYARI"
    assert flag.title == "Özkaynak negatif"


def test_small_equity_dip_does_not_trigger():
    result = _run(latest={"EQUITY": 490.0})  # -%2
    assert _flag(result, "equity_trend") is None


def test_equity_missing_is_not_evaluated():
    result = _run(drop=("EQUITY",))
    assert _unevaluated(result, "equity_trend").missing_fields == ["EQUITY"]


# --- Alacak / stok gelirden hızlı büyüyor --------------------------------------


def test_receivables_outpacing_revenue_triggers():
    result = _run(latest={"RECEIVABLES": 400.0})  # alacak +%100, gelir +%40
    flag = _flag(result, "receivables_vs_revenue")
    assert flag is not None
    assert flag.severity == "DIKKAT"
    values = {v.key: v.value for v in flag.values}
    assert values["receivables_growth_yoy"] == pytest.approx(1.0)
    assert values["revenue_growth_yoy"] == pytest.approx(0.4)


def test_receivables_flat_while_revenue_falls_triggers_with_honest_wording():
    result = _run(latest={"REVENUE": 800.0, "RECEIVABLES": 200.0})  # gelir -%20, alacak sabit
    flag = _flag(result, "receivables_vs_revenue")
    assert flag is not None
    assert "geriledi" in flag.detail


def test_receivables_in_line_with_revenue_does_not_trigger():
    result = _run(latest={"RECEIVABLES": 300.0})  # 1,5 / 1,4 - 1 = %7
    assert _flag(result, "receivables_vs_revenue") is None


def test_receivables_missing_is_not_evaluated():
    result = _run(drop=("RECEIVABLES",))
    check = _unevaluated(result, "receivables_vs_revenue")
    assert check.missing_fields == ["RECEIVABLES"]
    assert check.reason == "Gerekli veri eksik: Ticari alacaklar."
    assert "RECEIVABLES" in result.missing_fields


def test_inventory_outpacing_revenue_triggers():
    result = _run(latest={"INVENTORY": 300.0})  # stok +%100, gelir +%40
    flag = _flag(result, "inventory_vs_revenue")
    assert flag is not None
    assert flag.title == "Stoklar gelirden hızlı büyüyor"


def test_inventory_in_line_with_revenue_does_not_trigger():
    assert _flag(_run(), "inventory_vs_revenue") is None


def test_inventory_missing_is_not_evaluated():
    result = _run(drop=("INVENTORY",))
    assert _unevaluated(result, "inventory_vs_revenue").missing_fields == ["INVENTORY"]


# --- Genel özellikler ----------------------------------------------------------


def _everything_wrong():
    return _run(
        prev={"OPERATING_CASH_FLOW": 40.0, "CAPEX": -50.0},
        latest={
            "OPERATING_CASH_FLOW": 30.0,
            "CAPEX": -80.0,
            "EBITDA": 150.0,
            "NET_INCOME": 180.0,
            "TOTAL_DEBT": 700.0,
            "EQUITY": 400.0,
            "RECEIVABLES": 500.0,
            "INVENTORY": 400.0,
        },
    )


def test_flags_are_sorted_by_severity():
    result = _everything_wrong()
    order = {"UYARI": 0, "DIKKAT": 1, "OLUMLU": 2}
    severities = [order[f.severity] for f in result.flags]
    assert severities == sorted(severities)
    assert len(result.flags) >= 6


def test_flag_text_contains_no_numbers():
    # Rakamlar yalnızca `values`'ta ham durur; metinde rakam olursa LLM onu
    # tekrarlar ve halüsinasyon koruması (ham değerlere bakar) doğrulayamaz.
    for flag in _everything_wrong().flags:
        assert not re.search(r"\d", flag.title), flag.title
        assert not re.search(r"\d", flag.detail), flag.detail
