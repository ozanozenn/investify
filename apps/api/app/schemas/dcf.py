"""DCF Engine output schemas (roadmap section 13 / Phase 2).

Mirrors the honesty conventions used across the codebase: every
money/rate field is `float | None` (never guessed), and `missing_fields`
records exactly what could not be computed and why. `overridden_fields`
on `DcfAssumptions` records which assumptions came from the caller
(query params / explicit override) vs were derived from history or
defaulted from `config/dcf.yaml`, so a UI can visually distinguish
"your input" from "our estimate"."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class DcfAssumptions(BaseModel):
    revenue_growth_rate: float | None = None
    ebit_margin: float | None = None
    tax_rate: float | None = None
    da_percent_of_revenue: float | None = None
    capex_percent_of_revenue: float | None = None
    working_capital_change_percent_of_revenue: float | None = None
    wacc: float | None = None
    terminal_growth_rate: float | None = None
    net_debt: float | None = None
    shares_outstanding: float | None = None

    overridden_fields: list[str] = []


class DcfScenarioResult(BaseModel):
    scenario: Literal["bear", "base", "bull"]
    assumptions: DcfAssumptions
    projected_fcf: list[float] = []
    terminal_value: float | None = None
    enterprise_value: float | None = None
    equity_value: float | None = None
    intrinsic_value_per_share: float | None = None
    upside_vs_current_price: float | None = None
    missing_fields: list[str] = []


class SensitivityCell(BaseModel):
    wacc: float
    terminal_growth: float
    intrinsic_value_per_share: float | None = None


class DcfResult(BaseModel):
    bear: DcfScenarioResult
    base: DcfScenarioResult
    bull: DcfScenarioResult
    sensitivity_matrix: list[SensitivityCell] = []
    missing_fields: list[str] = []
