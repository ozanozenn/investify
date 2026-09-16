"""Discounted Cash Flow engine (roadmap section 13 / Phase 2).

Two-stage DCF (explicit projection + Gordon Growth terminal value) with
Bear/Base/Bull scenarios and a WACC x Terminal Growth sensitivity matrix.
Follows the house convention established in `valuation_engine/engine.py`:
pure functions, `None`/explicit `missing_fields` entries instead of
guessing, and every assumption traceable to either an explicit override,
a value derived from the company's own historical periods, or a
config-driven default (see `config/dcf.yaml`) — never invented.

ADR-003 note: this module is part of the deterministic engine layer. Its
output feeds the LLM interpretation layer like every other engine output;
the LLM never computes any of these numbers.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.financial_engine import formulas
from app.models.enums import CanonicalField as CF
from app.schemas.dcf import DcfAssumptions, DcfResult, DcfScenarioResult, SensitivityCell
from app.schemas.financial import PeriodData

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "dcf.yaml"

_OVERRIDABLE_FIELDS = (
    "revenue_growth_rate",
    "ebit_margin",
    "tax_rate",
    "da_percent_of_revenue",
    "capex_percent_of_revenue",
    "working_capital_change_percent_of_revenue",
    "wacc",
    "terminal_growth_rate",
    "net_debt",
    "shares_outstanding",
)


@lru_cache
def get_dcf_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _annual_periods_with(periods: list[PeriodData], *fields: CF) -> list[PeriodData]:
    """Annual periods carrying non-None values for every requested field,
    sorted ascending by fiscal year."""
    out = [
        p
        for p in periods
        if p.period_type == "ANNUAL" and all(p.values.get(f.value) is not None for f in fields)
    ]
    return sorted(out, key=lambda p: p.fiscal_year)


def _derive_revenue_growth(periods: list[PeriodData]) -> float | None:
    usable = _annual_periods_with(periods, CF.REVENUE)
    if len(usable) < 2:
        return None
    earliest, latest = usable[0], usable[-1]
    years = latest.fiscal_year - earliest.fiscal_year
    if years <= 0:
        return None
    return formulas.cagr(latest.values[CF.REVENUE.value], earliest.values[CF.REVENUE.value], years)


def _derive_ebit_margin(latest_period: PeriodData, periods: list[PeriodData]) -> float | None:
    if latest_period.values.get(CF.REVENUE.value) is not None and latest_period.values.get(CF.EBIT.value) is not None:
        m = formulas.margin(latest_period.values[CF.EBIT.value], latest_period.values[CF.REVENUE.value])
        if m is not None:
            return m
    usable = _annual_periods_with(periods, CF.REVENUE, CF.EBIT)
    if not usable:
        return None
    most_recent = usable[-1]
    return formulas.margin(most_recent.values[CF.EBIT.value], most_recent.values[CF.REVENUE.value])


def _derive_da_percent(latest_period: PeriodData, periods: list[PeriodData]) -> float | None:
    def da_margin(p: PeriodData) -> float | None:
        ebitda = p.values.get(CF.EBITDA.value)
        ebit = p.values.get(CF.EBIT.value)
        revenue = p.values.get(CF.REVENUE.value)
        if ebitda is None or ebit is None or revenue is None:
            return None
        return formulas.margin(ebitda - ebit, revenue)

    m = da_margin(latest_period)
    if m is not None:
        return m
    usable = _annual_periods_with(periods, CF.REVENUE, CF.EBITDA, CF.EBIT)
    if not usable:
        return None
    return da_margin(usable[-1])


def _derive_capex_percent(latest_period: PeriodData, periods: list[PeriodData]) -> float | None:
    def capex_margin(p: PeriodData) -> float | None:
        capex = p.values.get(CF.CAPEX.value)
        revenue = p.values.get(CF.REVENUE.value)
        if capex is None or revenue is None:
            return None
        return formulas.margin(abs(capex), revenue)

    m = capex_margin(latest_period)
    if m is not None:
        return m
    usable = _annual_periods_with(periods, CF.REVENUE, CF.CAPEX)
    if not usable:
        return None
    return capex_margin(usable[-1])


def _capm_wacc(config: dict, market_cap: float | None, net_debt: float | None, tax_rate: float) -> tuple[float, list[str]]:
    capm = config["capm"]
    beta = capm["default_beta"]
    cost_of_equity = capm["risk_free_rate"] + beta * capm["equity_risk_premium"]
    cost_of_debt_after_tax = capm["pretax_cost_of_debt"] * (1 - tax_rate)

    if market_cap is None or net_debt is None or (market_cap + net_debt) <= 0:
        # Insufficient market data to weight equity vs debt — fall back to
        # the config-implied WACC assuming an all-equity capital structure
        # rather than guessing a debt weight.
        return cost_of_equity, ["wacc_defaulted_insufficient_market_data"]

    equity_weight = market_cap / (market_cap + net_debt)
    debt_weight = 1 - equity_weight
    wacc = equity_weight * cost_of_equity + debt_weight * cost_of_debt_after_tax
    return wacc, []


def _derive_base_assumptions(
    latest_period: PeriodData | None,
    historical_periods: list[PeriodData],
    market_cap: float | None,
    net_debt_input: float | None,
    shares_outstanding_input: float | None,
    overrides: DcfAssumptions | None,
) -> tuple[DcfAssumptions, list[str]]:
    config = get_dcf_config()
    missing: list[str] = []
    overridden: list[str] = []

    def overridden_value(field: str):
        if overrides is not None:
            v = getattr(overrides, field)
            if v is not None:
                overridden.append(field)
                return v
        return None

    values: dict[str, float | None] = {}

    revenue_growth = overridden_value("revenue_growth_rate")
    if revenue_growth is None:
        revenue_growth = _derive_revenue_growth(historical_periods)
        if revenue_growth is None:
            revenue_growth = config["baseline_defaults"]["revenue_growth"]
            missing.append("revenue_growth_defaulted_from_config")
    values["revenue_growth_rate"] = revenue_growth

    ebit_margin = overridden_value("ebit_margin")
    if ebit_margin is None:
        ebit_margin = _derive_ebit_margin(latest_period, historical_periods)
        if ebit_margin is None:
            ebit_margin = config["baseline_defaults"]["ebit_margin"]
            missing.append("ebit_margin_defaulted_from_config")
    values["ebit_margin"] = ebit_margin

    tax_rate = overridden_value("tax_rate")
    if tax_rate is None:
        tax_rate = config["capm"]["default_tax_rate"]
        missing.append("tax_rate_defaulted_from_config")
    values["tax_rate"] = tax_rate

    da_percent = overridden_value("da_percent_of_revenue")
    if da_percent is None:
        da_percent = _derive_da_percent(latest_period, historical_periods)
        if da_percent is None:
            da_percent = config["baseline_defaults"]["da_percent_of_revenue"]
            missing.append("da_percent_of_revenue_defaulted_from_config")
    values["da_percent_of_revenue"] = da_percent

    capex_percent = overridden_value("capex_percent_of_revenue")
    if capex_percent is None:
        capex_percent = _derive_capex_percent(latest_period, historical_periods)
        if capex_percent is None:
            capex_percent = config["baseline_defaults"]["capex_percent_of_revenue"]
            missing.append("capex_percent_of_revenue_defaulted_from_config")
    values["capex_percent_of_revenue"] = capex_percent

    wc_percent = overridden_value("working_capital_change_percent_of_revenue")
    if wc_percent is None:
        # No canonical field carries working-capital movement — always
        # config-defaulted unless explicitly overridden.
        wc_percent = config["baseline_defaults"]["working_capital_change_percent_of_revenue"]
        missing.append("working_capital_change_percent_of_revenue_defaulted_from_config")
    values["working_capital_change_percent_of_revenue"] = wc_percent

    net_debt = overridden_value("net_debt")
    if net_debt is None:
        net_debt = net_debt_input
        if net_debt is None:
            missing.append("net_debt_unavailable")
    values["net_debt"] = net_debt

    shares_outstanding = overridden_value("shares_outstanding")
    if shares_outstanding is None:
        shares_outstanding = shares_outstanding_input
        if shares_outstanding is None:
            missing.append("shares_outstanding_unavailable")
    values["shares_outstanding"] = shares_outstanding

    terminal_growth = overridden_value("terminal_growth_rate")
    if terminal_growth is None:
        terminal_growth = config["terminal_growth_default"]
    values["terminal_growth_rate"] = terminal_growth

    wacc = overridden_value("wacc")
    if wacc is None:
        wacc, wacc_missing = _capm_wacc(config, market_cap, net_debt, tax_rate)
        missing.extend(wacc_missing)
    values["wacc"] = wacc

    assumptions = DcfAssumptions(**values, overridden_fields=overridden)
    return assumptions, missing


def _project_fcf(assumptions: DcfAssumptions, latest_revenue: float, projection_years: int) -> list[float]:
    revenue = latest_revenue
    fcfs: list[float] = []
    for _ in range(projection_years):
        revenue = revenue * (1 + assumptions.revenue_growth_rate)
        ebit = revenue * assumptions.ebit_margin
        fcf = (
            ebit * (1 - assumptions.tax_rate)
            + revenue * assumptions.da_percent_of_revenue
            - revenue * assumptions.capex_percent_of_revenue
            - revenue * assumptions.working_capital_change_percent_of_revenue
        )
        fcfs.append(fcf)
    return fcfs


def _value_scenario(
    scenario: str,
    assumptions: DcfAssumptions,
    latest_revenue: float,
    projection_years: int,
    current_price: float | None,
    extra_missing: list[str],
) -> DcfScenarioResult:
    """Single code path for Bear/Base/Bull and every sensitivity-matrix
    cell: project FCF, discount it, apply Gordon Growth terminal value."""
    missing = list(extra_missing)
    fcfs = _project_fcf(assumptions, latest_revenue, projection_years)

    wacc = assumptions.wacc
    g = assumptions.terminal_growth_rate
    if wacc is None or g is None or wacc <= g:
        missing.append("wacc_must_exceed_terminal_growth")
        return DcfScenarioResult(
            scenario=scenario,
            assumptions=assumptions,
            projected_fcf=fcfs,
            terminal_value=None,
            enterprise_value=None,
            equity_value=None,
            intrinsic_value_per_share=None,
            upside_vs_current_price=None,
            missing_fields=missing,
        )

    discounted_fcfs = [fcf / (1 + wacc) ** t for t, fcf in enumerate(fcfs, start=1)]
    raw_terminal_value = fcfs[-1] * (1 + g) / (wacc - g)
    discounted_terminal_value = raw_terminal_value / (1 + wacc) ** projection_years
    enterprise_value = sum(discounted_fcfs) + discounted_terminal_value

    if assumptions.net_debt is None:
        equity_value = None
        if "net_debt_unavailable" not in missing:
            missing.append("net_debt_unavailable")
    else:
        equity_value = enterprise_value - assumptions.net_debt

    intrinsic_value_per_share = None
    if equity_value is not None:
        if not assumptions.shares_outstanding:
            if "shares_outstanding_unavailable" not in missing:
                missing.append("shares_outstanding_unavailable")
        else:
            intrinsic_value_per_share = equity_value / assumptions.shares_outstanding

    upside = None
    if intrinsic_value_per_share is not None and current_price:
        upside = (intrinsic_value_per_share / current_price) - 1

    return DcfScenarioResult(
        scenario=scenario,
        assumptions=assumptions,
        projected_fcf=fcfs,
        terminal_value=discounted_terminal_value,
        enterprise_value=enterprise_value,
        equity_value=equity_value,
        intrinsic_value_per_share=intrinsic_value_per_share,
        upside_vs_current_price=upside,
        missing_fields=missing,
    )


def _empty_scenario(scenario: str, missing_fields: list[str]) -> DcfScenarioResult:
    return DcfScenarioResult(scenario=scenario, assumptions=DcfAssumptions(), missing_fields=missing_fields)


def _empty_result(missing_fields: list[str]) -> DcfResult:
    return DcfResult(
        bear=_empty_scenario("bear", missing_fields),
        base=_empty_scenario("base", missing_fields),
        bull=_empty_scenario("bull", missing_fields),
        sensitivity_matrix=[],
        missing_fields=missing_fields,
    )


def _frange(min_v: float, max_v: float, step: float) -> list[float]:
    if step <= 0:
        return [min_v]
    n = round((max_v - min_v) / step)
    return [round(min_v + i * step, 10) for i in range(n + 1)]


def compute_dcf(
    latest_period: PeriodData | None,
    historical_periods: list[PeriodData],
    current_price: float | None,
    market_cap: float | None,
    net_debt: float | None,
    shares_outstanding: float | None,
    overrides: DcfAssumptions | None = None,
) -> DcfResult:
    if latest_period is None:
        return _empty_result(["no_financial_period"])

    latest_revenue = latest_period.values.get(CF.REVENUE.value)
    if not latest_revenue or latest_revenue <= 0:
        return _empty_result(["revenue_unavailable"])

    config = get_dcf_config()
    projection_years = config["projection_years"]

    base_assumptions, base_missing = _derive_base_assumptions(
        latest_period, historical_periods, market_cap, net_debt, shares_outstanding, overrides
    )

    base_result = _value_scenario(
        "base", base_assumptions, latest_revenue, projection_years, current_price, base_missing
    )

    deltas = config["scenario_deltas"]

    def scenario_assumptions(delta_key: str) -> DcfAssumptions:
        d = deltas[delta_key]
        return base_assumptions.model_copy(
            update={
                "revenue_growth_rate": base_assumptions.revenue_growth_rate + d["revenue_growth"],
                "ebit_margin": base_assumptions.ebit_margin + d["ebit_margin"],
            }
        )

    bear_assumptions = scenario_assumptions("bear")
    bull_assumptions = scenario_assumptions("bull")

    bear_result = _value_scenario(
        "bear", bear_assumptions, latest_revenue, projection_years, current_price, list(base_missing)
    )
    bull_result = _value_scenario(
        "bull", bull_assumptions, latest_revenue, projection_years, current_price, list(base_missing)
    )

    sensitivity_matrix: list[SensitivityCell] = []
    matrix_cfg = config["sensitivity_matrix"]
    wacc_cfg = matrix_cfg["wacc_range"]
    growth_cfg = matrix_cfg["terminal_growth_range"]
    wacc_grid = _frange(wacc_cfg["min"], wacc_cfg["max"], wacc_cfg["step"])
    growth_grid = _frange(growth_cfg["min"], growth_cfg["max"], growth_cfg["step"])
    for wacc in wacc_grid:
        for g in growth_grid:
            cell_assumptions = base_assumptions.model_copy(update={"wacc": wacc, "terminal_growth_rate": g})
            cell_result = _value_scenario(
                "base", cell_assumptions, latest_revenue, projection_years, current_price, []
            )
            sensitivity_matrix.append(
                SensitivityCell(
                    wacc=wacc,
                    terminal_growth=g,
                    intrinsic_value_per_share=cell_result.intrinsic_value_per_share,
                )
            )

    top_missing = sorted(set(bear_result.missing_fields) | set(base_result.missing_fields) | set(bull_result.missing_fields))

    return DcfResult(
        bear=bear_result,
        base=base_result,
        bull=bull_result,
        sensitivity_matrix=sensitivity_matrix,
        missing_fields=top_missing,
    )
