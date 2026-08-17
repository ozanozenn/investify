from __future__ import annotations

from pydantic import BaseModel


class ValuationMetrics(BaseModel):
    """Deterministic output of valuation_engine (roadmap section 12 / 3.6).
    Phase 1 scope: relative valuation vs the company's own trailing history.
    DCF is intentionally absent — see docs/PHASE_1_SCOPE.md — but this
    schema has room to grow a `dcf: DcfResult | None` field later without
    breaking consumers (ADR-001)."""

    pe: float | None = None
    pb: float | None = None
    ev_ebitda: float | None = None

    pe_historical_median: float | None = None
    pb_historical_median: float | None = None
    ev_ebitda_historical_median: float | None = None

    pe_vs_history_ratio: float | None = None
    pb_vs_history_ratio: float | None = None
    ev_ebitda_vs_history_ratio: float | None = None

    history_years_used: int = 0
    missing_fields: list[str] = []
