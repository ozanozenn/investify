import datetime as dt

import pytest

from app.schemas.dcf import DcfAssumptions
from app.schemas.financial import PeriodData
from app.valuation_engine.dcf import compute_dcf, get_dcf_config


def _period(year: int, revenue, ebit=None, ebitda=None, capex=None) -> PeriodData:
    values = {"REVENUE": revenue}
    if ebit is not None:
        values["EBIT"] = ebit
    if ebitda is not None:
        values["EBITDA"] = ebitda
    if capex is not None:
        values["CAPEX"] = capex
    return PeriodData(
        period_type="ANNUAL",
        fiscal_year=year,
        period_end_date=dt.date(year, 12, 31),
        values=values,
    )


def _rich_periods():
    """Two annual periods with REVENUE/EBIT/EBITDA/CAPEX so revenue growth,
    EBIT margin, D&A%, and CAPEX% are all derivable from history rather
    than defaulted."""
    p2023 = _period(2023, revenue=1000, ebit=150, ebitda=200, capex=-40)
    p2024 = _period(2024, revenue=1200, ebit=190, ebitda=250, capex=-50)
    return p2024, [p2023, p2024]


def test_compute_dcf_bear_base_bull_ordering():
    latest, historical = _rich_periods()
    result = compute_dcf(
        latest_period=latest,
        historical_periods=historical,
        current_price=20.0,
        market_cap=10_000.0,
        net_debt=500.0,
        shares_outstanding=500.0,
    )

    assert result.bear.intrinsic_value_per_share is not None
    assert result.base.intrinsic_value_per_share is not None
    assert result.bull.intrinsic_value_per_share is not None
    assert result.bear.intrinsic_value_per_share < result.base.intrinsic_value_per_share
    assert result.base.intrinsic_value_per_share < result.bull.intrinsic_value_per_share

    # Revenue growth / EBIT margin should be derived from history, not defaulted.
    assert "revenue_growth_defaulted_from_config" not in result.base.missing_fields
    assert "ebit_margin_defaulted_from_config" not in result.base.missing_fields
    assert result.base.assumptions.revenue_growth_rate == pytest.approx(0.2)
    assert result.base.assumptions.ebit_margin == pytest.approx(190 / 1200)

    # Enterprise value should always be positive/finite for the base case.
    assert result.base.enterprise_value is not None
    assert result.base.upside_vs_current_price is not None


def test_compute_dcf_missing_shares_outstanding_keeps_enterprise_value():
    latest, historical = _rich_periods()
    result = compute_dcf(
        latest_period=latest,
        historical_periods=historical,
        current_price=None,
        market_cap=10_000.0,
        net_debt=500.0,
        shares_outstanding=None,
    )

    base = result.base
    assert base.enterprise_value is not None
    assert base.equity_value is not None
    assert base.intrinsic_value_per_share is None
    assert base.upside_vs_current_price is None
    assert "shares_outstanding_unavailable" in base.missing_fields
    assert "shares_outstanding_unavailable" in result.missing_fields


def test_compute_dcf_wacc_must_exceed_terminal_growth_guard():
    latest, historical = _rich_periods()
    overrides = DcfAssumptions(wacc=0.10, terminal_growth_rate=0.15)
    result = compute_dcf(
        latest_period=latest,
        historical_periods=historical,
        current_price=20.0,
        market_cap=10_000.0,
        net_debt=500.0,
        shares_outstanding=500.0,
        overrides=overrides,
    )

    base = result.base
    assert base.terminal_value is None
    assert base.enterprise_value is None
    assert base.equity_value is None
    assert base.intrinsic_value_per_share is None
    assert "wacc_must_exceed_terminal_growth" in base.missing_fields
    # Must not raise or produce a nonsensical (e.g. negative) value.


def test_compute_dcf_sensitivity_matrix_shape():
    latest, historical = _rich_periods()
    result = compute_dcf(
        latest_period=latest,
        historical_periods=historical,
        current_price=20.0,
        market_cap=10_000.0,
        net_debt=500.0,
        shares_outstanding=500.0,
    )

    config = get_dcf_config()
    wacc_cfg = config["sensitivity_matrix"]["wacc_range"]
    growth_cfg = config["sensitivity_matrix"]["terminal_growth_range"]
    expected_wacc_points = round((wacc_cfg["max"] - wacc_cfg["min"]) / wacc_cfg["step"]) + 1
    expected_growth_points = round((growth_cfg["max"] - growth_cfg["min"]) / growth_cfg["step"]) + 1

    assert len(result.sensitivity_matrix) == expected_wacc_points * expected_growth_points
    waccs = {cell.wacc for cell in result.sensitivity_matrix}
    growths = {cell.terminal_growth for cell in result.sensitivity_matrix}
    assert len(waccs) == expected_wacc_points
    assert len(growths) == expected_growth_points


def test_compute_dcf_override_respected_and_recorded():
    latest, historical = _rich_periods()
    overrides = DcfAssumptions(wacc=0.30)
    result = compute_dcf(
        latest_period=latest,
        historical_periods=historical,
        current_price=20.0,
        market_cap=10_000.0,
        net_debt=500.0,
        shares_outstanding=500.0,
        overrides=overrides,
    )

    assert result.base.assumptions.wacc == pytest.approx(0.30)
    assert "wacc" in result.base.assumptions.overridden_fields
    # Bear/Bull inherit the overridden WACC too (only revenue growth/EBIT
    # margin are scenario-shifted).
    assert result.bear.assumptions.wacc == pytest.approx(0.30)
    assert result.bull.assumptions.wacc == pytest.approx(0.30)


def test_compute_dcf_no_period_returns_empty():
    result = compute_dcf(
        latest_period=None,
        historical_periods=[],
        current_price=None,
        market_cap=None,
        net_debt=None,
        shares_outstanding=None,
    )
    assert result.missing_fields == ["no_financial_period"]
    assert result.base.intrinsic_value_per_share is None
