from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel


class MetricDelta(BaseModel):
    """One tracked metric's change between two snapshots (roadmap section 26)."""

    metric: str  # machine key, e.g. "revenue_growth_yoy"
    label: str  # human label, e.g. "Revenue growth (YoY)"
    previous: float | None
    current: float | None
    delta: float | None  # current - previous; None if either side is missing
    is_notable: bool


class SnapshotDiffResult(BaseModel):
    """Output of comparing two `AnalysisSnapshot` rows for the same ticker
    (roadmap sections 25 "Thesis Tracking" / 26 "Change Detection"). Every
    field here is derived by plain Python comparison of already-computed,
    deterministic engine output — no LLM involved (ADR-003)."""

    ticker: str
    from_snapshot_id: int
    to_snapshot_id: int
    from_as_of: dt.datetime
    to_as_of: dt.datetime

    deltas: list[MetricDelta]
    notable_changes: list[MetricDelta]

    valuation_direction: Literal["cheaper", "more_expensive", "unchanged", "unknown"]

    overall_score_delta: float | None
    thesis_strength: Literal["STRENGTHENED", "WEAKENED", "UNCHANGED"]
    thesis_strength_reason: str
