"""Deterministic data quality / confidence scoring (roadmap section 38 / 75).
Never an LLM's own self-assessed confidence — derived from completeness,
freshness and metric coverage, per config/analysis.yaml weights.
"""

from __future__ import annotations

from app.core.config import get_analysis_config
from app.schemas.context import DataQuality
from app.schemas.financial import FinancialMetrics


def compute_data_quality(
    metrics: FinancialMetrics,
    stage_results: dict[str, str],
    market_available: bool,
) -> DataQuality:
    cfg = get_analysis_config()["data_quality"]["weights"]
    warnings: list[str] = []

    total_core_fields = 9  # see financial_engine.engine.REQUIRED_FOR_CORE_METRICS
    missing = len(metrics.missing_fields)
    completeness = max(0.0, 1 - missing / total_core_fields)
    if missing:
        warnings.append(f"{missing} core financial field(s) missing for latest period")

    failed_stages = [name for name, status in stage_results.items() if status == "FAILED"]
    freshness = max(0.0, 1 - 0.2 * len(failed_stages))
    for stage in failed_stages:
        warnings.append(f"{stage} data unavailable")
    if not market_available:
        warnings.append("market data unavailable")
        freshness = min(freshness, 0.5)

    tracked_metrics = [
        metrics.revenue_growth_yoy,
        metrics.ebitda_margin,
        metrics.net_margin,
        metrics.roe,
        metrics.net_debt_to_ebitda,
        metrics.debt_to_equity,
        metrics.fcf_margin,
    ]
    coverage = sum(1 for m in tracked_metrics if m is not None) / len(tracked_metrics)

    overall = round(
        completeness * cfg["completeness"] + freshness * cfg["freshness"] + coverage * cfg["metric_coverage"],
        3,
    )
    return DataQuality(
        completeness=round(completeness, 3),
        freshness=round(freshness, 3),
        metric_coverage=round(coverage, 3),
        overall=overall,
        warnings=warnings,
    )
