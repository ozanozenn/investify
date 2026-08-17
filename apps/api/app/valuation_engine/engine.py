"""Basic relative valuation engine (roadmap section 12 / Phase 1 3.6).

Computes current P/E, P/B, EV/EBITDA from live market data, and an
approximate historical comparison using the company's own trailing annual
periods matched to the nearest historical close price.

Documented simplification (see docs/PHASE_1_SCOPE.md "Known limitations"):
historical enterprise value/market cap reconstruction assumes the CURRENT
share count applied to HISTORICAL prices (`shares_outstanding` is not
tracked per-period). For companies with material share issuance/buybacks
across the lookback window this biases the historical multiples; full DCF
and per-period share-count tracking is Phase 2+ scope. The bias is
disclosed in `ValuationMetrics.missing_fields` as a warning whenever a
computation used it, so the LLM/UI can caveat it rather than presenting it
as exact.
"""

from __future__ import annotations

import datetime as dt
import statistics

from app.models.enums import CanonicalField as CF
from app.providers.base import Candle
from app.schemas.financial import PeriodData
from app.schemas.valuation import ValuationMetrics


def _nearest_close(candles: list[Candle], target: dt.date, max_gap_days: int = 10) -> float | None:
    best: tuple[int, float] | None = None
    for c in candles:
        gap = abs((c.date - target).days)
        if gap <= max_gap_days and (best is None or gap < best[0]):
            best = (gap, c.close)
    return best[1] if best else None


def compute_valuation(
    current_price: float | None,
    market_cap: float | None,
    shares_outstanding: float | None,
    latest_period: PeriodData | None,
    historical_periods: list[PeriodData],
    historical_candles: list[Candle],
    lookback_years: int = 5,
) -> ValuationMetrics:
    missing: list[str] = []
    if latest_period is None:
        return ValuationMetrics(missing_fields=["no_financial_period"])

    net_income = latest_period.values.get(CF.NET_INCOME.value)
    equity = latest_period.values.get(CF.EQUITY.value)
    ebitda = latest_period.values.get(CF.EBITDA.value)
    total_debt = latest_period.values.get(CF.TOTAL_DEBT.value)
    cash = latest_period.values.get(CF.CASH.value)
    net_debt = (total_debt - cash) if (total_debt is not None and cash is not None) else None
    ev = (market_cap + net_debt) if (market_cap is not None and net_debt is not None) else None

    pe = market_cap / net_income if market_cap and net_income and net_income > 0 else None
    pb = market_cap / equity if market_cap and equity and equity > 0 else None
    ev_ebitda = ev / ebitda if ev is not None and ebitda and ebitda > 0 else None
    if pe is None:
        missing.append("pe_unavailable")
    if pb is None:
        missing.append("pb_unavailable")
    if ev_ebitda is None:
        missing.append("ev_ebitda_unavailable")

    hist_pe, hist_pb, hist_ev_ebitda = [], [], []
    window = sorted(historical_periods, key=lambda p: p.fiscal_year)[-(lookback_years):]
    window = [p for p in window if p is not latest_period and p.fiscal_year != latest_period.fiscal_year]
    if window and shares_outstanding:
        missing.append("historical_valuation_uses_current_share_count_approximation")
    for period in window:
        close = _nearest_close(historical_candles, period.period_end_date)
        if close is None or not shares_outstanding:
            continue
        hist_market_cap = close * shares_outstanding
        p_ni = period.values.get(CF.NET_INCOME.value)
        p_eq = period.values.get(CF.EQUITY.value)
        p_ebitda = period.values.get(CF.EBITDA.value)
        p_debt = period.values.get(CF.TOTAL_DEBT.value)
        p_cash = period.values.get(CF.CASH.value)
        p_net_debt = (p_debt - p_cash) if (p_debt is not None and p_cash is not None) else None
        p_ev = hist_market_cap + p_net_debt if p_net_debt is not None else None

        if p_ni and p_ni > 0:
            hist_pe.append(hist_market_cap / p_ni)
        if p_eq and p_eq > 0:
            hist_pb.append(hist_market_cap / p_eq)
        if p_ev is not None and p_ebitda and p_ebitda > 0:
            hist_ev_ebitda.append(p_ev / p_ebitda)

    pe_median = statistics.median(hist_pe) if hist_pe else None
    pb_median = statistics.median(hist_pb) if hist_pb else None
    ev_ebitda_median = statistics.median(hist_ev_ebitda) if hist_ev_ebitda else None

    return ValuationMetrics(
        pe=pe,
        pb=pb,
        ev_ebitda=ev_ebitda,
        pe_historical_median=pe_median,
        pb_historical_median=pb_median,
        ev_ebitda_historical_median=ev_ebitda_median,
        pe_vs_history_ratio=(pe / pe_median) if pe and pe_median else None,
        pb_vs_history_ratio=(pb / pb_median) if pb and pb_median else None,
        ev_ebitda_vs_history_ratio=(ev_ebitda / ev_ebitda_median) if ev_ebitda and ev_ebitda_median else None,
        history_years_used=len(window),
        missing_fields=missing,
    )
