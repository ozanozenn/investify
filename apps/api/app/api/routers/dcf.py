"""Read-only DCF endpoint (roadmap section 13 / Phase 2).

Self-contained new router — not yet wired into `app/main.py` (a separate
integration pass does that, per `docs/PHASE_2_PLAN.md` Wave 2). Reuses the
same "load the latest AnalysisSnapshot" pattern as
`app/api/routers/companies.py::get_company_analysis`, then reconstructs
just enough `PeriodData`-shaped history from the snapshot's persisted
`context_json` (a `StructuredAnalysisContext.model_dump()`) to feed
`compute_dcf`.

Known gap (see docs/PHASE_2_PLAN.md / final report for detail): the
persisted context's `financial_history` entries
(`app.schemas.financial.FinancialHistoryPoint`) carry only
`fiscal_year, revenue, ebitda, net_income, free_cash_flow` — no EBIT, no
CAPEX, no per-period net debt or share count, and no exact
`period_end_date`. We deliberately do NOT invent EBIT/CAPEX from EBITDA or
guess a period end date beyond assuming a calendar fiscal year (Dec 31),
consistent with how this codebase already treats annual periods
elsewhere. Net debt comes from `metrics.net_debt` (latest point-in-time).
Share count is not present in the context at all; we derive an
approximation as `market_cap / price` when both are available, and
otherwise leave it absent — `compute_dcf` then reports
`shares_outstanding_unavailable` in `missing_fields` rather than guessing.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import require_user
from app.models.enums import CanonicalField as CF
from app.models.snapshots import AnalysisSnapshot
from app.schemas.dcf import DcfAssumptions, DcfResult
from app.schemas.financial import PeriodData
from app.valuation_engine.dcf import compute_dcf

router = APIRouter(prefix="/api/companies", tags=["dcf"], dependencies=[Depends(require_user)])


def _periods_from_context(context: dict) -> tuple[PeriodData | None, list[PeriodData]]:
    """Reconstruct annual PeriodData objects from a persisted
    StructuredAnalysisContext's `financial_history`. Only fields actually
    present in FinancialHistoryPoint are populated (see module docstring
    for the exact gap vs a full PeriodData)."""
    points = context.get("financial_history") or []
    periods: list[PeriodData] = []
    for point in points:
        fiscal_year = point.get("fiscal_year")
        if fiscal_year is None:
            continue
        values: dict[str, float] = {}
        if point.get("revenue") is not None:
            values[CF.REVENUE.value] = point["revenue"]
        if point.get("ebitda") is not None:
            values[CF.EBITDA.value] = point["ebitda"]
        if point.get("net_income") is not None:
            values[CF.NET_INCOME.value] = point["net_income"]
        if point.get("free_cash_flow") is not None:
            values[CF.FREE_CASH_FLOW.value] = point["free_cash_flow"]
        periods.append(
            PeriodData(
                period_type="ANNUAL",
                fiscal_year=fiscal_year,
                # FinancialHistoryPoint carries no exact period end date;
                # calendar fiscal year end is the same assumption already
                # used for annual periods elsewhere in this codebase.
                period_end_date=dt.date(fiscal_year, 12, 31),
                values=values,
            )
        )
    periods.sort(key=lambda p: p.fiscal_year)
    latest_period = periods[-1] if periods else None
    return latest_period, periods


def _overrides_from_query(
    revenue_growth_rate: float | None,
    ebit_margin: float | None,
    tax_rate: float | None,
    da_percent_of_revenue: float | None,
    capex_percent_of_revenue: float | None,
    working_capital_change_percent_of_revenue: float | None,
    wacc: float | None,
    terminal_growth_rate: float | None,
    net_debt: float | None,
    shares_outstanding: float | None,
) -> DcfAssumptions | None:
    fields = {
        "revenue_growth_rate": revenue_growth_rate,
        "ebit_margin": ebit_margin,
        "tax_rate": tax_rate,
        "da_percent_of_revenue": da_percent_of_revenue,
        "capex_percent_of_revenue": capex_percent_of_revenue,
        "working_capital_change_percent_of_revenue": working_capital_change_percent_of_revenue,
        "wacc": wacc,
        "terminal_growth_rate": terminal_growth_rate,
        "net_debt": net_debt,
        "shares_outstanding": shares_outstanding,
    }
    if all(v is None for v in fields.values()):
        return None
    return DcfAssumptions(**fields)


@router.get("/{ticker}/analysis/dcf", response_model=DcfResult)
async def get_company_dcf(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    revenue_growth_rate: float | None = Query(default=None),
    ebit_margin: float | None = Query(default=None),
    tax_rate: float | None = Query(default=None),
    da_percent_of_revenue: float | None = Query(default=None),
    capex_percent_of_revenue: float | None = Query(default=None),
    working_capital_change_percent_of_revenue: float | None = Query(default=None),
    wacc: float | None = Query(default=None),
    terminal_growth_rate: float | None = Query(default=None),
    net_debt: float | None = Query(default=None),
    shares_outstanding: float | None = Query(default=None),
):
    ticker = ticker.upper()
    result = await db.execute(
        select(AnalysisSnapshot).where(AnalysisSnapshot.ticker == ticker).order_by(AnalysisSnapshot.created_at.desc()).limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"No analysis yet for {ticker} — run a refresh first.")

    ctx = snapshot.context_json
    market = ctx.get("market") or {}
    metrics = ctx.get("metrics") or {}

    current_price = market.get("price")
    market_cap = market.get("market_cap")
    net_debt_from_context = metrics.get("net_debt")

    shares_outstanding_derived = None
    if market_cap and current_price:
        shares_outstanding_derived = market_cap / current_price

    latest_period, historical_periods = _periods_from_context(ctx)

    overrides = _overrides_from_query(
        revenue_growth_rate,
        ebit_margin,
        tax_rate,
        da_percent_of_revenue,
        capex_percent_of_revenue,
        working_capital_change_percent_of_revenue,
        wacc,
        terminal_growth_rate,
        net_debt,
        shares_outstanding,
    )

    return compute_dcf(
        latest_period=latest_period,
        historical_periods=historical_periods,
        current_price=current_price,
        market_cap=market_cap,
        net_debt=net_debt_from_context,
        shares_outstanding=shares_outstanding_derived,
        overrides=overrides,
    )
