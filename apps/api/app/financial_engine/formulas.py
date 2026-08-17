"""Financial Formula Registry (roadmap section 60).

Every formula here is a pure function: typed numeric inputs in, a single
`float | None` out. `None` means "cannot be computed with the data
available" — formulas never guess or silently substitute a default. Full
prose definitions + edge cases are mirrored in docs/FINANCIAL_ENGINE.md;
keep the two in sync when changing a formula (and bump
`Settings.financial_engine_version`, per ADR-005, if the *result* of an
existing formula would change for the same inputs).
"""

from __future__ import annotations


def safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def growth_rate(current: float | None, previous: float | None) -> float | None:
    """(current - previous) / abs(previous). None if previous is 0/None or
    current is None — a growth rate from a zero base is not meaningful."""
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / abs(previous)


def cagr(latest: float | None, earliest: float | None, years: int) -> float | None:
    """Compound annual growth rate. Requires same-sign, non-zero
    `earliest` (a CAGR across a sign change is undefined) and years > 0."""
    if latest is None or earliest is None or years <= 0:
        return None
    if earliest <= 0 or latest <= 0:
        return None
    return (latest / earliest) ** (1 / years) - 1


def margin(numerator: float | None, revenue: float | None) -> float | None:
    return safe_div(numerator, revenue)


def net_debt(total_debt: float | None, cash: float | None) -> float | None:
    if total_debt is None or cash is None:
        return None
    return total_debt - cash


def leverage_ratio(numerator: float | None, denominator: float | None) -> float | None:
    """Generic x/y leverage ratio (Net Debt/EBITDA, Debt/Equity, ...).
    None if denominator is missing/zero/negative (a negative-equity
    Debt/Equity ratio is not comparable across companies and is
    intentionally suppressed rather than shown as a misleading number)."""
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def average(a: float | None, b: float | None) -> float | None:
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return (a + b) / 2


def free_cash_flow(operating_cash_flow: float | None, capex: float | None) -> float | None:
    """FCF = OCF - |CAPEX|. Provider CAPEX sign conventions vary (Yahoo
    reports it negative); we normalize to a magnitude subtraction so the
    formula is correct regardless of the source's sign convention."""
    if operating_cash_flow is None or capex is None:
        return None
    return operating_cash_flow - abs(capex)


def growth_consistency(growth_rates: list[float | None]) -> float | None:
    """Fraction (0..1) of the given YoY growth rates that are positive.
    None if there are no computable growth rates at all."""
    valid = [g for g in growth_rates if g is not None]
    if not valid:
        return None
    return sum(1 for g in valid if g > 0) / len(valid)
