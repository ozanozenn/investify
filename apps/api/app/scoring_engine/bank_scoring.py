"""Banka skorlaması (ADR-014).

Genel skorla aynı kategori anahtarlarını (`ScoreResult`) ve aynı bileşen
puanlama kuralını (`engine.score_category`) kullanır; yalnızca bileşenler ve
ağırlıklar `config/bank_scoring.yaml`'dan gelir. `cash_flow` bankada
anlamsızdır: ağırlığı 0'dır ve değer üretilmez, sadece nedeni yazılır.
"""

from __future__ import annotations

from functools import lru_cache

import yaml

from app.core.config import CONFIG_DIR
from app.schemas.scoring import CategoryScore, ScoreComponent, ScoreResult
from app.scoring_engine.engine import score_category

_SCORED_CATEGORIES = ("growth", "profitability", "balance_sheet", "valuation")


@lru_cache
def get_bank_scoring_config() -> dict:
    with open(CONFIG_DIR / "bank_scoring.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _excluded_category(cfg: dict) -> CategoryScore:
    return CategoryScore(
        label=cfg["label"],
        score=0.0,
        components=[
            ScoreComponent(
                metric="not_applicable_bank",
                label=cfg["label"],
                value=None,
                points=0.0,
                max_points=0.0,
                reason=cfg["reason"],
            )
        ],
    )


def compute_bank_score(metrics: dict[str, float | None], config: dict | None = None) -> ScoreResult:
    cfg = config or get_bank_scoring_config()
    categories = {key: score_category(key, cfg["categories"][key], metrics) for key in _SCORED_CATEGORIES}
    weights: dict[str, float] = cfg["overall_weights"]
    overall = round(sum(categories[k].score * w for k, w in weights.items() if k in categories), 1)

    return ScoreResult(
        growth=categories["growth"],
        profitability=categories["profitability"],
        balance_sheet=categories["balance_sheet"],
        cash_flow=_excluded_category(cfg["excluded_categories"]["cash_flow"]),
        valuation=categories["valuation"],
        overall=overall,
        overall_weights=weights,
        engine_version=cfg["version"],
    )
