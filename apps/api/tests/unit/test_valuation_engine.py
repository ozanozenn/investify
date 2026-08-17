import datetime as dt

import pytest

from app.providers.base import Candle
from app.schemas.financial import PeriodData
from app.valuation_engine.engine import compute_valuation


def _period(year: int, net_income, equity, ebitda, total_debt, cash) -> PeriodData:
    return PeriodData(
        period_type="ANNUAL",
        fiscal_year=year,
        period_end_date=dt.date(year, 12, 31),
        values={
            "NET_INCOME": net_income,
            "EQUITY": equity,
            "EBITDA": ebitda,
            "TOTAL_DEBT": total_debt,
            "CASH": cash,
        },
    )


def test_compute_valuation_current_and_historical():
    latest = _period(2025, net_income=100, equity=1000, ebitda=200, total_debt=300, cash=100)
    historical = [
        _period(2024, net_income=80, equity=900, ebitda=180, total_debt=280, cash=90),
        latest,
    ]
    candles = [Candle(date=dt.date(2024, 12, 31), open=39, high=41, low=38, close=40, volume=1000)]

    result = compute_valuation(
        current_price=50,
        market_cap=5000,
        shares_outstanding=100,
        latest_period=latest,
        historical_periods=historical,
        historical_candles=candles,
        lookback_years=5,
    )

    assert result.pe == pytest.approx(50.0)
    assert result.pb == pytest.approx(5.0)
    assert result.ev_ebitda == pytest.approx(26.0)
    assert result.pe_historical_median == pytest.approx(50.0)
    assert result.ev_ebitda_historical_median == pytest.approx(4190 / 180)
    assert result.pe_vs_history_ratio == pytest.approx(1.0)
    assert "historical_valuation_uses_current_share_count_approximation" in result.missing_fields


def test_compute_valuation_no_period_returns_empty():
    result = compute_valuation(
        current_price=None,
        market_cap=None,
        shares_outstanding=None,
        latest_period=None,
        historical_periods=[],
        historical_candles=[],
    )
    assert result.pe is None
    assert result.missing_fields == ["no_financial_period"]


def test_compute_valuation_negative_net_income_suppresses_pe():
    latest = _period(2025, net_income=-50, equity=1000, ebitda=200, total_debt=300, cash=100)
    result = compute_valuation(
        current_price=50,
        market_cap=5000,
        shares_outstanding=100,
        latest_period=latest,
        historical_periods=[latest],
        historical_candles=[],
    )
    assert result.pe is None  # a P/E on negative earnings is not meaningful
    assert result.pb == pytest.approx(5.0)
