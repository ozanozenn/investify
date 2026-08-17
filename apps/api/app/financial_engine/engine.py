from __future__ import annotations

from app.financial_engine import formulas as f
from app.models.enums import CanonicalField as CF
from app.schemas.financial import FinancialMetrics, PeriodData

REQUIRED_FOR_CORE_METRICS = [
    CF.REVENUE.value,
    CF.EBITDA.value,
    CF.NET_INCOME.value,
    CF.EQUITY.value,
    CF.TOTAL_DEBT.value,
    CF.CASH.value,
    CF.TOTAL_ASSETS.value,
    CF.OPERATING_CASH_FLOW.value,
    CF.CAPEX.value,
]


def _get(period: PeriodData, field: CF) -> float | None:
    return period.values.get(field.value)


def _fcf(period: PeriodData) -> float | None:
    explicit = _get(period, CF.FREE_CASH_FLOW)
    if explicit is not None:
        return explicit
    return f.free_cash_flow(_get(period, CF.OPERATING_CASH_FLOW), _get(period, CF.CAPEX))


def compute_financial_metrics(annual_periods: list[PeriodData]) -> FinancialMetrics:
    """`annual_periods` must be sorted ascending by fiscal_year. Uses the
    latest period as "current" and, where needed, up to the last 4 periods
    for growth/CAGR/consistency."""
    if not annual_periods:
        return FinancialMetrics(as_of_period="N/A", missing_fields=["no_financial_periods"])

    periods = sorted(annual_periods, key=lambda p: p.fiscal_year)
    latest = periods[-1]
    previous = periods[-2] if len(periods) >= 2 else None

    revenue = _get(latest, CF.REVENUE)
    ebitda = _get(latest, CF.EBITDA)
    net_income = _get(latest, CF.NET_INCOME)
    equity = _get(latest, CF.EQUITY)
    total_debt = _get(latest, CF.TOTAL_DEBT)
    cash = _get(latest, CF.CASH)
    total_assets = _get(latest, CF.TOTAL_ASSETS)
    ocf = _get(latest, CF.OPERATING_CASH_FLOW)
    fcf = _fcf(latest)

    prev_revenue = _get(previous, CF.REVENUE) if previous else None
    prev_ebitda = _get(previous, CF.EBITDA) if previous else None
    prev_net_income = _get(previous, CF.NET_INCOME) if previous else None
    prev_equity = _get(previous, CF.EQUITY) if previous else None

    nd = f.net_debt(total_debt, cash)

    # Revenue CAGR 3Y: use up to 4 annual points spanning up to 3 years.
    cagr_window = periods[-4:] if len(periods) >= 4 else periods
    revenue_cagr_3y = None
    if len(cagr_window) >= 2:
        years_span = cagr_window[-1].fiscal_year - cagr_window[0].fiscal_year
        revenue_cagr_3y = f.cagr(_get(cagr_window[-1], CF.REVENUE), _get(cagr_window[0], CF.REVENUE), years_span)

    # Growth consistency over up to the last 3 YoY transitions.
    growth_rates: list[float | None] = []
    for i in range(max(1, len(periods) - 3), len(periods)):
        growth_rates.append(f.growth_rate(_get(periods[i], CF.REVENUE), _get(periods[i - 1], CF.REVENUE)))

    metrics = FinancialMetrics(
        as_of_period=str(latest.fiscal_year),
        revenue_growth_yoy=f.growth_rate(revenue, prev_revenue),
        revenue_cagr_3y=revenue_cagr_3y,
        ebitda_growth_yoy=f.growth_rate(ebitda, prev_ebitda),
        ebitda_margin=f.margin(ebitda, revenue),
        net_income_growth_yoy=f.growth_rate(net_income, prev_net_income),
        net_margin=f.margin(net_income, revenue),
        roe=f.safe_div(net_income, f.average(equity, prev_equity)),
        net_debt=nd,
        net_debt_to_ebitda=f.leverage_ratio(nd, ebitda) if nd is not None else None,
        debt_to_equity=f.leverage_ratio(total_debt, equity),
        equity_ratio=f.safe_div(equity, total_assets),
        operating_cash_flow=ocf,
        ocf_margin=f.margin(ocf, revenue),
        free_cash_flow=fcf,
        fcf_margin=f.margin(fcf, revenue),
        fcf_conversion=f.safe_div(fcf, net_income) if net_income and net_income > 0 else None,
        growth_consistency=f.growth_consistency(growth_rates),
        latest_revenue=revenue,
        latest_ebitda=ebitda,
        latest_net_income=net_income,
    )
    metrics.missing_fields = [
        field for field in REQUIRED_FOR_CORE_METRICS if _get(latest, CF(field)) is None
    ]
    return metrics
