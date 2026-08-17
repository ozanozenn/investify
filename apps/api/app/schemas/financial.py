from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class PeriodData(BaseModel):
    period_type: str
    fiscal_year: int
    fiscal_quarter: int | None = None
    period_end_date: dt.date
    values: dict[str, float]


class FinancialHistoryPoint(BaseModel):
    """One annual data point for the Company Detail "Financial Performance"
    charts (roadmap section 3.14). Distinct from `FinancialMetrics`, which
    is a single point-in-time snapshot of ratios — this is the raw
    multi-year series the UI plots."""

    fiscal_year: int
    revenue: float | None = None
    ebitda: float | None = None
    net_income: float | None = None
    free_cash_flow: float | None = None


class FinancialMetrics(BaseModel):
    """Deterministic output of financial_engine (roadmap section 10 / 3.5).
    Every field is None (never guessed) when its required inputs are
    missing — see docs/FINANCIAL_ENGINE.md for exact formulas."""

    as_of_period: str

    revenue_growth_yoy: float | None = None
    revenue_cagr_3y: float | None = None
    ebitda_growth_yoy: float | None = None
    ebitda_margin: float | None = None
    net_income_growth_yoy: float | None = None
    net_margin: float | None = None
    roe: float | None = None

    net_debt: float | None = None
    net_debt_to_ebitda: float | None = None
    debt_to_equity: float | None = None
    equity_ratio: float | None = None

    operating_cash_flow: float | None = None
    ocf_margin: float | None = None
    free_cash_flow: float | None = None
    fcf_margin: float | None = None
    fcf_conversion: float | None = None

    growth_consistency: float | None = None

    latest_revenue: float | None = None
    latest_ebitda: float | None = None
    latest_net_income: float | None = None

    missing_fields: list[str] = []
