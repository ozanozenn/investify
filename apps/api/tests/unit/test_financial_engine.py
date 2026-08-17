import math

from app.financial_engine.engine import compute_financial_metrics
from tests.fixtures.thyao_like import annual_periods


def approx(a, b, tol=1e-6):
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def test_compute_financial_metrics_full_history():
    metrics = compute_financial_metrics(annual_periods())

    assert metrics.as_of_period == "2025"
    assert approx(metrics.revenue_growth_yoy, 0.1)
    assert approx(metrics.ebitda_growth_yoy, 0.12)
    assert approx(metrics.net_income_growth_yoy, 0.15)
    assert approx(metrics.ebitda_margin, 280 / 1331)
    assert approx(metrics.net_margin, 115 / 1331)
    assert approx(metrics.roe, 115 / 655)
    assert approx(metrics.net_debt, 190.0)
    assert approx(metrics.net_debt_to_ebitda, 190 / 280)
    assert approx(metrics.debt_to_equity, 340 / 690)
    assert approx(metrics.equity_ratio, 690 / 1350)
    assert approx(metrics.free_cash_flow, 145.0)
    assert approx(metrics.fcf_margin, 145 / 1331)
    assert approx(metrics.fcf_conversion, 145 / 115)
    assert approx(metrics.ocf_margin, 210 / 1331)
    assert approx(metrics.revenue_cagr_3y, 0.1, tol=1e-4)
    assert approx(metrics.growth_consistency, 1.0)
    assert metrics.missing_fields == []


def test_compute_financial_metrics_single_period_has_no_growth():
    metrics = compute_financial_metrics(annual_periods()[-1:])
    assert metrics.revenue_growth_yoy is None
    assert metrics.ebitda_growth_yoy is None
    assert metrics.net_income_growth_yoy is None
    # margin/leverage don't need a previous period
    assert metrics.ebitda_margin is not None
    assert metrics.net_debt_to_ebitda is not None


def test_compute_financial_metrics_no_periods_returns_empty_result():
    metrics = compute_financial_metrics([])
    assert metrics.as_of_period == "N/A"
    assert metrics.missing_fields == ["no_financial_periods"]
    assert metrics.revenue_growth_yoy is None


def test_missing_field_is_reported_not_guessed():
    periods = annual_periods()
    periods[-1].values.pop("CASH")
    metrics = compute_financial_metrics(periods)
    assert "CASH" in metrics.missing_fields
    assert metrics.net_debt is None  # cannot compute without cash
    assert metrics.net_debt_to_ebitda is None
