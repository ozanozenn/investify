"""Reel büyüme (ADR-016): (1 + nominal) / (1 + TÜFE) - 1; mock TÜFE ile asla."""

from __future__ import annotations

import datetime as dt

import pytest

from app.financial_engine import formulas as f
from app.financial_engine.real_growth import compute_real_growth
from app.schemas.context import MacroSeriesPoint
from app.schemas.financial import PeriodData

MAX_GAP = 12


def _period(year: int, revenue: float | None = None, net_income: float | None = None) -> PeriodData:
    values = {}
    if revenue is not None:
        values["REVENUE"] = revenue
    if net_income is not None:
        values["NET_INCOME"] = net_income
    return PeriodData(period_type="ANNUAL", fiscal_year=year, period_end_date=dt.date(year, 12, 31), values=values)


def _cpi(value: float = 30.0, *, is_mock: bool = False, observed: dt.date = dt.date(2026, 1, 1)) -> MacroSeriesPoint:
    return MacroSeriesPoint(code="cpi_yoy", label="TÜFE (Yıllık)", value=value, observation_date=observed, is_mock=is_mock)


PERIODS = [_period(2024, revenue=1000.0, net_income=100.0), _period(2025, revenue=1400.0, net_income=120.0)]


def test_formula_deflates_nominal_growth():
    assert f.real_growth(0.40, 0.30) == pytest.approx(1.4 / 1.3 - 1)
    assert f.real_growth(0.30, 0.45) == pytest.approx(1.3 / 1.45 - 1)  # enflasyonun altında = reel küçülme
    assert f.real_growth(None, 0.30) is None
    assert f.real_growth(0.40, None) is None
    assert f.real_growth(0.40, -1.0) is None


def test_real_growth_with_real_cpi():
    rg = compute_real_growth(PERIODS, _cpi(30.0), MAX_GAP)
    assert rg.as_of_period == "2025"
    assert rg.cpi_yoy == pytest.approx(0.30)  # yüzde puan -> 0-1 oran
    assert rg.cpi_observation_date == dt.date(2026, 1, 1)
    assert rg.revenue_growth_nominal == pytest.approx(0.40)
    assert rg.revenue_growth_real == pytest.approx(1.4 / 1.3 - 1)
    assert rg.net_income_growth_nominal == pytest.approx(0.20)
    assert rg.net_income_growth_real == pytest.approx(1.2 / 1.3 - 1)
    assert rg.net_income_growth_real < 0  # nominal +%20, enflasyon %30 -> reel küçülme
    assert rg.missing_fields == []


def test_mock_cpi_never_produces_real_growth():
    rg = compute_real_growth(PERIODS, _cpi(30.0, is_mock=True), MAX_GAP)
    assert rg.revenue_growth_real is None
    assert rg.net_income_growth_real is None
    assert rg.cpi_yoy is None  # mock değer gerçekmiş gibi taşınmaz
    assert rg.revenue_growth_nominal == pytest.approx(0.40)  # nominal yine var
    assert rg.missing_fields == ["cpi_yoy_mock"]


def test_missing_cpi_is_reported():
    rg = compute_real_growth(PERIODS, None, MAX_GAP)
    assert rg.revenue_growth_real is None
    assert rg.missing_fields == ["cpi_yoy"]


def test_cpi_far_from_fiscal_year_end_is_rejected():
    rg = compute_real_growth(PERIODS, _cpi(30.0, observed=dt.date(2027, 7, 1)), MAX_GAP)  # 19 ay
    assert rg.revenue_growth_real is None
    assert rg.cpi_yoy == pytest.approx(0.30)  # şeffaflık için gösterilir
    assert rg.missing_fields == ["cpi_period_mismatch"]


def test_net_income_from_loss_base_is_not_deflated():
    periods = [_period(2024, revenue=1000.0, net_income=-50.0), _period(2025, revenue=1400.0, net_income=100.0)]
    rg = compute_real_growth(periods, _cpi(30.0), MAX_GAP)
    assert rg.revenue_growth_real == pytest.approx(1.4 / 1.3 - 1)
    assert rg.net_income_growth_nominal == pytest.approx(3.0)  # FinancialMetrics ile aynı |önceki| tabanlı
    assert rg.net_income_growth_real is None
    assert rg.missing_fields == ["non_positive_base:NET_INCOME"]


def test_missing_revenue_and_single_period():
    periods = [_period(2024, net_income=100.0), _period(2025, net_income=120.0)]
    rg = compute_real_growth(periods, _cpi(), MAX_GAP)
    assert rg.revenue_growth_real is None
    assert "REVENUE" in rg.missing_fields

    single = compute_real_growth([_period(2025, revenue=1.0, net_income=1.0)], _cpi(), MAX_GAP)
    assert single.revenue_growth_nominal is None
    assert "previous_period" in single.missing_fields

    empty = compute_real_growth([], _cpi(), MAX_GAP)
    assert empty.missing_fields == ["no_financial_periods"]
