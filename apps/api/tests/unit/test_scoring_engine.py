import pytest

from app.scoring_engine.engine import _interpolate, compute_score, score_category


def test_interpolate_clamps_outside_range():
    breakpoints = [[0.0, 0], [1.0, 10]]
    assert _interpolate(breakpoints, -5) == 0
    assert _interpolate(breakpoints, 5) == 10


def test_interpolate_linear_midpoint():
    breakpoints = [[0.0, 0], [1.0, 10]]
    assert _interpolate(breakpoints, 0.5) == pytest.approx(5.0)


def test_score_category_excludes_missing_metric_and_rescales():
    cfg = {
        "label": "Test",
        "components": [
            {"metric": "a", "label": "A", "max_points": 50, "breakpoints": [[0, 0], [1, 50]]},
            {"metric": "b", "label": "B", "max_points": 50, "breakpoints": [[0, 0], [1, 50]]},
        ],
    }
    # Only "a" is available at its max (1.0 -> 50/50); "b" is missing entirely.
    result = score_category("test", cfg, {"a": 1.0})
    # Rescaled over the applicable max (50, not 100): should be 100, not 50.
    assert result.score == 100.0
    assert result.components[1].value is None
    assert result.components[1].points == 0.0
    assert "hariç tutuldu" in result.components[1].reason


def test_score_category_all_missing_yields_zero_not_error():
    cfg = {
        "label": "Test",
        "components": [{"metric": "a", "label": "A", "max_points": 100, "breakpoints": [[0, 0], [1, 100]]}],
    }
    result = score_category("test", cfg, {})
    assert result.score == 0.0


def test_compute_score_uses_real_config_and_produces_overall_in_range():
    metrics = {
        "revenue_growth_yoy": 0.1,
        "ebitda_growth_yoy": 0.12,
        "net_income_growth_yoy": 0.15,
        "growth_consistency": 1.0,
        "ebitda_margin": 0.21,
        "net_margin": 0.086,
        "roe": 0.17,
        "net_debt_to_ebitda": 0.68,
        "debt_to_equity": 0.49,
        "equity_ratio": 0.51,
        "ocf_margin": 0.16,
        "fcf_margin": 0.11,
        "fcf_conversion": 1.26,
        "pe_vs_history_ratio": 1.0,
        "ev_ebitda_vs_history_ratio": 1.0,
        "pb_vs_history_ratio": 1.0,
    }
    result = compute_score(metrics, engine_version="v1")
    assert 0 <= result.overall <= 100
    assert result.engine_version == "v1"
    # Strong, consistent growth + healthy leverage should score comfortably above the midpoint.
    assert result.growth.score > 60
    assert result.balance_sheet.score > 50
