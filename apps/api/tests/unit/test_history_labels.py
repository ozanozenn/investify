"""Değerleme kutucuklarının etiketleri hüküm kartıyla aynı eşikleri kullanmalı."""

from __future__ import annotations

import pytest

from app.core.config import get_verdict_config
from app.schemas.scoring import CategoryScore, ScoreResult
from app.schemas.valuation import ValuationMetrics
from app.verdict_engine.engine import compute_verdict
from app.verdict_engine.history_labels import label_history_multiples

_HISTORY = get_verdict_config()["lenses"]["history"]
_CHEAP, _EXPENSIVE = _HISTORY["cheap_below"], _HISTORY["expensive_above"]


def _label(valuation: ValuationMetrics) -> ValuationMetrics:
    return label_history_multiples(valuation, cheap_below=_CHEAP, expensive_above=_EXPENSIVE)


def _history_lens_verdict(valuation: ValuationMetrics) -> str | None:
    cat = CategoryScore(label="x", score=60, components=[])
    scores = ScoreResult(
        growth=cat, profitability=cat, balance_sheet=cat, cash_flow=cat, valuation=cat,
        overall=60, overall_weights={}, engine_version="v1",
    )
    verdict = compute_verdict(valuation, scores, 0.9, None, get_verdict_config())
    return next(lens.verdict for lens in verdict.lenses if lens.key == "history")


# Eşiklerin iki yanı ve tam üstü — sınır davranışı da aynı olmalı.
_RATIOS = [0.5, _CHEAP - 0.001, _CHEAP, 1.0, _EXPENSIVE, _EXPENSIVE + 0.001, 2.0]


@pytest.mark.parametrize("multiple", ["pe", "pb", "ev_ebitda"])
@pytest.mark.parametrize("ratio", _RATIOS)
def test_tile_label_matches_verdict_history_lens(multiple, ratio):
    """Tek çarpan varken hüküm kartının tarihsel yöntemi o çarpanın oranına
    bakar; kutucuk etiketi ile birebir aynı olmalı."""
    valuation = ValuationMetrics(**{f"{multiple}_vs_history_ratio": ratio}, history_years_used=5)

    labelled = _label(valuation)

    assert getattr(labelled, f"{multiple}_vs_history_label") == _history_lens_verdict(valuation)
    assert getattr(labelled, f"{multiple}_vs_history_diff") == pytest.approx(ratio - 1)


def test_thresholds_are_arguments_not_hardcoded():
    valuation = ValuationMetrics(pe_vs_history_ratio=1.1)
    strict = label_history_multiples(valuation, cheap_below=0.95, expensive_above=1.05)
    assert strict.pe_vs_history_label == "PAHALI"


def test_missing_ratio_stays_none_and_input_is_not_mutated():
    valuation = ValuationMetrics(pe_vs_history_ratio=_EXPENSIVE * 2, pb_vs_history_ratio=None, ev_ebitda_vs_history_ratio=None)

    labelled = _label(valuation)

    assert labelled.pe_vs_history_label == "PAHALI"
    assert labelled.pb_vs_history_label is None and labelled.pb_vs_history_diff is None
    assert labelled.ev_ebitda_vs_history_label is None and labelled.ev_ebitda_vs_history_diff is None
    assert valuation.pe_vs_history_label is None  # saf: girdi değişmedi


def test_old_snapshot_without_label_fields_still_parses():
    old = {"pe": 10.0, "pe_historical_median": 8.0, "pe_vs_history_ratio": 1.25, "history_years_used": 4, "missing_fields": []}
    parsed = ValuationMetrics.model_validate(old)
    assert parsed.pe_vs_history_label is None
    assert parsed.pe_vs_history_diff is None
