from __future__ import annotations

from pydantic import BaseModel


class ScoreComponent(BaseModel):
    metric: str
    label: str
    value: float | None
    points: float
    max_points: float
    reason: str


class CategoryScore(BaseModel):
    label: str
    score: float
    components: list[ScoreComponent]


class ScoreResult(BaseModel):
    growth: CategoryScore
    profitability: CategoryScore
    balance_sheet: CategoryScore
    cash_flow: CategoryScore
    valuation: CategoryScore
    overall: float
    overall_weights: dict[str, float]
    engine_version: str
    unsupported_reason: str | None = None
