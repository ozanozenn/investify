from __future__ import annotations

from pydantic import BaseModel

from app.schemas.dcf import DcfResult


class ValuationMetrics(BaseModel):
    """Deterministic output of valuation_engine (roadmap section 12 / 3.6).
    Phase 1 scope was relative valuation vs the company's own trailing
    history; Phase 2 (roadmap section 13) adds `dcf`, computed separately
    by `valuation_engine/dcf.py` and attached in `refresh_pipeline.py` —
    exactly the growth path this schema's docstring anticipated
    (ADR-001)."""

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

    dcf: DcfResult | None = None
