"""Snapshot diff / thesis tracking (roadmap sections 25 "Thesis Tracking"
and 26 "Change Detection").

Pure, deterministic comparison of two `AnalysisSnapshot` rows for the same
ticker. Every value here is plain Python arithmetic over already-computed
engine output (`context_json`) — no LLM call, consistent with ADR-003's
"the LLM never computes numbers" rule applying to the whole system, not
just the original analysis pipeline.

Config-driven thresholds (no magic numbers, mirrors `scoring_engine/engine.py`
+ `config/scoring.yaml`) live in `config/thesis.yaml` and are loaded via a
local `@lru_cache` loader, independent of `app/core/config.py`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml

from app.models.snapshots import AnalysisSnapshot
from app.schemas.diff import MetricDelta, SnapshotDiffResult

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

# (metric key used in thesis.yaml / MetricDelta.metric, context_json section,
# key within that section, human label).
_TRACKED_METRICS: list[tuple[str, str, str, str]] = [
    ("revenue_growth_yoy", "metrics", "revenue_growth_yoy", "Revenue growth (YoY)"),
    ("ebitda_margin", "metrics", "ebitda_margin", "EBITDA margin"),
    ("net_debt_to_ebitda", "metrics", "net_debt_to_ebitda", "Net Debt / EBITDA"),
    ("roe", "metrics", "roe", "Return on Equity (ROE)"),
    ("pe", "valuation", "pe", "P/E"),
    ("overall_score", "scores", "overall", "Overall score"),
]


@lru_cache
def _get_thesis_config() -> dict[str, Any]:
    with open(CONFIG_DIR / "thesis.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _extract(context_json: dict, section: str, json_key: str) -> float | None:
    return (context_json.get(section) or {}).get(json_key)


def _build_delta(
    metric_key: str,
    section: str,
    json_key: str,
    label: str,
    previous_ctx: dict,
    current_ctx: dict,
    thresholds: dict[str, float],
) -> MetricDelta:
    previous_value = _extract(previous_ctx, section, json_key)
    current_value = _extract(current_ctx, section, json_key)

    delta: float | None = None
    is_notable = False
    if previous_value is not None and current_value is not None:
        delta = current_value - previous_value
        threshold = thresholds.get(metric_key)
        if threshold is not None:
            is_notable = abs(delta) >= threshold

    return MetricDelta(
        metric=metric_key,
        label=label,
        previous=previous_value,
        current=current_value,
        delta=delta,
        is_notable=is_notable,
    )


def _valuation_direction(
    previous_ctx: dict, current_ctx: dict
) -> Literal["cheaper", "more_expensive", "unchanged", "unknown"]:
    """Compares raw P/E directly between the two snapshots.

    We deliberately do NOT use `pe_vs_history_ratio` here: that field
    answers a different question ("is this snapshot rich/cheap vs this
    company's own trailing history"), whereas "cheaper / more expensive"
    in the thesis-tracking sense (roadmap section 25) is asking whether
    THIS snapshot is cheaper than the PREVIOUS snapshot — a direct P/E
    comparison is the correct signal for that question.
    """
    previous_pe = _extract(previous_ctx, "valuation", "pe")
    current_pe = _extract(current_ctx, "valuation", "pe")
    if previous_pe is None or current_pe is None:
        return "unknown"
    if current_pe < previous_pe:
        return "cheaper"
    if current_pe > previous_pe:
        return "more_expensive"
    return "unchanged"


def _classify_thesis_strength(
    overall_score_delta: float | None, strength_cfg: dict[str, float]
) -> tuple[Literal["STRENGTHENED", "WEAKENED", "UNCHANGED"], str]:
    strengthened_at = strength_cfg.get("strengthened_at_or_above", 3.0)
    weakened_at = strength_cfg.get("weakened_at_or_below", -3.0)

    if overall_score_delta is None:
        return "UNCHANGED", "Overall score unavailable on one of the two snapshots; unable to assess change."
    if overall_score_delta >= strengthened_at:
        return "STRENGTHENED", f"Overall score improved by {overall_score_delta:.1f} points"
    if overall_score_delta <= weakened_at:
        return "WEAKENED", f"Overall score declined by {abs(overall_score_delta):.1f} points"
    return (
        "UNCHANGED",
        f"Overall score changed by {overall_score_delta:+.1f} points, within the no-change threshold",
    )


def compute_snapshot_diff(previous: AnalysisSnapshot, current: AnalysisSnapshot) -> SnapshotDiffResult:
    """Pure function: no DB session, no I/O beyond the cached YAML load.

    `previous`/`current` need only expose `.id`, `.ticker`, `.as_of` and
    `.context_json` — real `AnalysisSnapshot` ORM instances work without a
    session (as used by the API router), and lightweight standalone
    instances work equally well in tests.
    """
    cfg = _get_thesis_config()
    thresholds: dict[str, float] = cfg.get("notable_change_thresholds", {})
    strength_cfg: dict[str, float] = cfg.get("thesis_strength", {})

    previous_ctx = previous.context_json
    current_ctx = current.context_json

    deltas = [
        _build_delta(metric_key, section, json_key, label, previous_ctx, current_ctx, thresholds)
        for metric_key, section, json_key, label in _TRACKED_METRICS
    ]
    notable_changes = [d for d in deltas if d.is_notable]

    overall_delta_metric = next(d for d in deltas if d.metric == "overall_score")
    overall_score_delta = overall_delta_metric.delta

    thesis_strength, thesis_strength_reason = _classify_thesis_strength(overall_score_delta, strength_cfg)
    valuation_direction = _valuation_direction(previous_ctx, current_ctx)

    return SnapshotDiffResult(
        ticker=current.ticker,
        from_snapshot_id=previous.id,
        to_snapshot_id=current.id,
        from_as_of=previous.as_of,
        to_as_of=current.as_of,
        deltas=deltas,
        notable_changes=notable_changes,
        valuation_direction=valuation_direction,
        overall_score_delta=overall_score_delta,
        thesis_strength=thesis_strength,
        thesis_strength_reason=thesis_strength_reason,
    )
