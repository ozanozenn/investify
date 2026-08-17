import pytest

from app.financial_engine import formulas as f


def test_safe_div_handles_none_and_zero():
    assert f.safe_div(10, 2) == 5
    assert f.safe_div(10, 0) is None
    assert f.safe_div(None, 2) is None
    assert f.safe_div(10, None) is None


def test_growth_rate_zero_base_is_none():
    assert f.growth_rate(110, 100) == 0.1
    assert f.growth_rate(110, 0) is None
    assert f.growth_rate(None, 100) is None


def test_cagr_requires_positive_same_sign_values():
    assert f.cagr(1331, 1000, 3) == pytest.approx(0.1)
    assert f.cagr(100, -50, 2) is None  # sign change across the window is undefined
    assert f.cagr(100, 50, 0) is None  # zero-year span


def test_leverage_ratio_rejects_nonpositive_denominator():
    assert f.leverage_ratio(100, 50) == 2.0
    assert f.leverage_ratio(100, 0) is None
    assert f.leverage_ratio(100, -50) is None  # negative equity D/E is not comparable


def test_free_cash_flow_normalizes_capex_sign():
    # Yahoo reports CAPEX negative; formula must work regardless of sign convention.
    assert f.free_cash_flow(200, -50) == 150
    assert f.free_cash_flow(200, 50) == 150


def test_growth_consistency_ignores_missing_values():
    assert f.growth_consistency([0.1, -0.05, 0.2]) == pytest.approx(2 / 3)
    assert f.growth_consistency([None, None]) is None
    assert f.growth_consistency([]) is None
