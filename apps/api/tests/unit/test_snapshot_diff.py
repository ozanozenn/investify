import datetime as dt

import pytest

from app.models.snapshots import AnalysisSnapshot
from app.services.snapshot_diff import compute_snapshot_diff


def _snapshot(id: int, as_of: dt.datetime, *, revenue_growth_yoy, ebitda_margin, net_debt_to_ebitda, roe, pe, overall) -> AnalysisSnapshot:
    """Builds a standalone `AnalysisSnapshot` ORM instance (no DB session
    needed — `compute_snapshot_diff` only reads plain attributes) with a
    `context_json` shaped like the real `StructuredAnalysisContext`."""
    return AnalysisSnapshot(
        id=id,
        company_id=1,
        ticker="THYAO",
        as_of=as_of,
        financial_engine_version="v1",
        scoring_engine_version="v1",
        valuation_engine_version="v1",
        prompt_version="company-analysis-v1",
        llm_model="mock",
        llm_is_mocked=True,
        context_json={
            "metrics": {
                "revenue_growth_yoy": revenue_growth_yoy,
                "ebitda_margin": ebitda_margin,
                "net_debt_to_ebitda": net_debt_to_ebitda,
                "roe": roe,
            },
            "valuation": {"pe": pe},
            "scores": {"overall": overall},
        },
        analysis_json={},
        data_quality_json={},
        created_at=as_of,
    )


# The roadmap's own worked example (section 25): all four metrics move
# unfavorably, so we expect a WEAKENED thesis.
PREVIOUS = _snapshot(
    id=1,
    as_of=dt.datetime(2026, 8, 17, tzinfo=dt.timezone.utc),
    revenue_growth_yoy=0.24,
    ebitda_margin=0.21,
    net_debt_to_ebitda=0.8,
    roe=0.27,
    pe=8.0,
    overall=78.0,
)
CURRENT = _snapshot(
    id=2,
    as_of=dt.datetime(2026, 11, 17, tzinfo=dt.timezone.utc),
    revenue_growth_yoy=0.18,
    ebitda_margin=0.18,
    net_debt_to_ebitda=1.4,
    roe=0.22,
    pe=10.0,
    overall=72.0,
)


def _delta_for(result, metric: str):
    return next(d for d in result.deltas if d.metric == metric)


def test_all_tracked_deltas_are_correct():
    result = compute_snapshot_diff(previous=PREVIOUS, current=CURRENT)

    assert _delta_for(result, "revenue_growth_yoy").delta == pytest.approx(0.18 - 0.24)
    assert _delta_for(result, "ebitda_margin").delta == pytest.approx(0.18 - 0.21)
    assert _delta_for(result, "net_debt_to_ebitda").delta == pytest.approx(1.4 - 0.8)
    assert _delta_for(result, "roe").delta == pytest.approx(0.22 - 0.27)
    assert _delta_for(result, "overall_score").delta == pytest.approx(72.0 - 78.0)


def test_notable_change_filter_includes_and_excludes_correctly():
    result = compute_snapshot_diff(previous=PREVIOUS, current=CURRENT)
    notable_metrics = {d.metric for d in result.notable_changes}

    # Clearly notable: net_debt_to_ebitda moves by 0.6, well above the
    # configured 0.2 threshold (config/thesis.yaml).
    nd = _delta_for(result, "net_debt_to_ebitda")
    assert nd.is_notable is True
    assert "net_debt_to_ebitda" in notable_metrics

    # Clearly notable: revenue growth moves 6 points, above the 0.03 threshold.
    rg = _delta_for(result, "revenue_growth_yoy")
    assert rg.is_notable is True

    # Construct a clearly-NOT-notable case: a metric that barely moves,
    # well under its threshold.
    flat_previous = _snapshot(
        id=10,
        as_of=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
        revenue_growth_yoy=0.10,
        ebitda_margin=0.20,
        net_debt_to_ebitda=1.0,
        roe=0.15,
        pe=9.0,
        overall=70.0,
    )
    flat_current = _snapshot(
        id=11,
        as_of=dt.datetime(2026, 2, 1, tzinfo=dt.timezone.utc),
        revenue_growth_yoy=0.10,
        ebitda_margin=0.205,  # +0.005, under the 0.02 threshold
        net_debt_to_ebitda=1.0,
        roe=0.15,
        pe=9.0,
        overall=70.5,  # +0.5, under the 3.0 threshold
    )
    flat_result = compute_snapshot_diff(previous=flat_previous, current=flat_current)
    ebitda_delta = _delta_for(flat_result, "ebitda_margin")
    assert ebitda_delta.is_notable is False
    assert ebitda_delta.metric not in {d.metric for d in flat_result.notable_changes}


def test_thesis_strength_weakened_for_roadmap_example():
    result = compute_snapshot_diff(previous=PREVIOUS, current=CURRENT)

    assert result.overall_score_delta == pytest.approx(-6.0)
    assert result.thesis_strength == "WEAKENED"
    assert "declined" in result.thesis_strength_reason
    assert result.valuation_direction == "more_expensive"  # PE rose 8.0 -> 10.0


def test_thesis_strength_strengthened_when_score_improves():
    better = _snapshot(
        id=20,
        as_of=dt.datetime(2026, 12, 1, tzinfo=dt.timezone.utc),
        revenue_growth_yoy=0.30,
        ebitda_margin=0.25,
        net_debt_to_ebitda=0.5,
        roe=0.30,
        pe=7.0,
        overall=85.0,
    )
    result = compute_snapshot_diff(previous=PREVIOUS, current=better)
    assert result.thesis_strength == "STRENGTHENED"
    assert "improved" in result.thesis_strength_reason
    assert result.valuation_direction == "cheaper"  # PE fell 8.0 -> 7.0


def test_missing_metric_on_one_side_yields_none_delta_and_not_notable():
    previous_missing_roe = _snapshot(
        id=30,
        as_of=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
        revenue_growth_yoy=0.1,
        ebitda_margin=0.2,
        net_debt_to_ebitda=1.0,
        roe=None,
        pe=None,
        overall=60.0,
    )
    current_has_roe = _snapshot(
        id=31,
        as_of=dt.datetime(2026, 2, 1, tzinfo=dt.timezone.utc),
        revenue_growth_yoy=0.1,
        ebitda_margin=0.2,
        net_debt_to_ebitda=1.0,
        roe=0.2,
        pe=9.0,
        overall=60.0,
    )
    result = compute_snapshot_diff(previous=previous_missing_roe, current=current_has_roe)

    roe_delta = _delta_for(result, "roe")
    assert roe_delta.previous is None
    assert roe_delta.current == pytest.approx(0.2)
    assert roe_delta.delta is None
    assert roe_delta.is_notable is False

    pe_delta = _delta_for(result, "pe")
    assert pe_delta.delta is None
    assert pe_delta.is_notable is False
    assert result.valuation_direction == "unknown"


def test_diff_result_carries_snapshot_identity():
    result = compute_snapshot_diff(previous=PREVIOUS, current=CURRENT)
    assert result.ticker == "THYAO"
    assert result.from_snapshot_id == 1
    assert result.to_snapshot_id == 2
    assert result.from_as_of == PREVIOUS.as_of
    assert result.to_as_of == CURRENT.as_of
