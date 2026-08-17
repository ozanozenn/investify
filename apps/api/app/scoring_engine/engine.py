"""Deterministic, explainable scoring engine (roadmap section 17 / 3.9).

Reads its entire definition from config/scoring.yaml (ADR — no magic
numbers in code, section 59). Each category score is a sum of component
point-contributions; see config/scoring.yaml's header comment for the
piecewise-linear interpolation contract and the missing-component rescale
rule.
"""

from __future__ import annotations

import bisect

from app.core.config import get_scoring_config
from app.schemas.scoring import CategoryScore, ScoreComponent, ScoreResult


def _interpolate(breakpoints: list[list[float]], x: float) -> float:
    xs = [p[0] for p in breakpoints]
    ys = [p[1] for p in breakpoints]
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    i = bisect.bisect_right(xs, x) - 1
    x0, x1 = xs[i], xs[i + 1]
    y0, y1 = ys[i], ys[i + 1]
    if x1 == x0:
        return y1
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def score_category(category_key: str, category_cfg: dict, metrics: dict[str, float | None]) -> CategoryScore:
    components: list[ScoreComponent] = []
    applicable_max = 0.0
    raw_points = 0.0

    for comp_cfg in category_cfg["components"]:
        metric_name = comp_cfg["metric"]
        value = metrics.get(metric_name)
        max_points = float(comp_cfg["max_points"])
        if value is None:
            components.append(
                ScoreComponent(
                    metric=metric_name,
                    label=comp_cfg["label"],
                    value=None,
                    points=0.0,
                    max_points=max_points,
                    reason="excluded: required data unavailable",
                )
            )
            continue
        points = _interpolate(comp_cfg["breakpoints"], value)
        points = max(0.0, min(points, max_points))
        applicable_max += max_points
        raw_points += points
        components.append(
            ScoreComponent(
                metric=metric_name,
                label=comp_cfg["label"],
                value=value,
                points=round(points, 2),
                max_points=max_points,
                reason=f"{comp_cfg['label']}={_fmt(value)} -> {round(points, 1)}/{max_points} pts",
            )
        )

    score = round((raw_points / applicable_max) * 100, 1) if applicable_max > 0 else 0.0
    return CategoryScore(label=category_cfg["label"], score=score, components=components)


def _fmt(value: float) -> str:
    return f"{value:.4g}"


def compute_score(metrics: dict[str, float | None], engine_version: str = "v1") -> ScoreResult:
    cfg = get_scoring_config()
    categories = {
        key: score_category(key, cat_cfg, metrics) for key, cat_cfg in cfg["categories"].items()
    }
    weights: dict[str, float] = cfg["overall_weights"]
    overall = round(sum(categories[k].score * w for k, w in weights.items()), 1)

    return ScoreResult(
        growth=categories["growth"],
        profitability=categories["profitability"],
        balance_sheet=categories["balance_sheet"],
        cash_flow=categories["cash_flow"],
        valuation=categories["valuation"],
        overall=overall,
        overall_weights=weights,
        engine_version=engine_version,
    )


def unsupported_score_result(engine_version: str, reason: str) -> ScoreResult:
    empty = CategoryScore(label="Unsupported", score=0.0, components=[])
    return ScoreResult(
        growth=empty,
        profitability=empty,
        balance_sheet=empty,
        cash_flow=empty,
        valuation=empty,
        overall=0.0,
        overall_weights={},
        engine_version=engine_version,
        unsupported_reason=reason,
    )
