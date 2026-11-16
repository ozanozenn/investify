"""Bankada hüküm: yalnızca tarihsel ve sektör yöntemleri oy verir (ADR-014)."""

from __future__ import annotations

import copy

import pytest

from app.core.config import get_verdict_config
from app.financial_engine.industry_strategy import BANK_DCF_NOT_APPLICABLE_MESSAGE
from app.schemas.dcf import DcfResult, DcfScenarioResult
from app.schemas.scoring import CategoryScore, ScoreResult
from app.schemas.valuation import ValuationMetrics
from app.verdict_engine.engine import PeerMedians, compute_verdict


def _scores(overall: float) -> ScoreResult:
    cat = CategoryScore(label="x", score=overall, components=[])
    return ScoreResult(
        growth=cat, profitability=cat, balance_sheet=cat, cash_flow=cat, valuation=cat,
        overall=overall, overall_weights={}, engine_version="bank-v1",
    )


@pytest.fixture
def cfg():
    return copy.deepcopy(get_verdict_config())


def _dcf_lens(verdict):
    return next(lens for lens in verdict.lenses if lens.key == "dcf")


def test_bank_dcf_lens_does_not_vote_and_explains_in_turkish(cfg):
    valuation = ValuationMetrics(pe=5.0, pb=1.0, pb_vs_history_ratio=0.7, history_years_used=4)
    v = compute_verdict(
        valuation, _scores(70), 0.9,
        PeerMedians(peer_count=3, median_pe=6.0, median_pb=1.4, pe_count=3, pb_count=3), cfg,
        dcf_not_applicable_reason=BANK_DCF_NOT_APPLICABLE_MESSAGE,
    )
    dcf = _dcf_lens(v)
    assert dcf.verdict is None
    assert dcf.not_applicable is True
    assert dcf.reason.startswith("Bankalar için DCF uygulanmaz")
    # Uygulanmayan yöntem eksik veri sayılmaz; iki yöntem oy verir.
    assert "verdict_lens_dcf" not in v.missing_fields
    assert v.price == "UCUZ"
    assert v.agreement == 1.0
    assert v.confidence == "YUKSEK"
    assert "2 değerleme yönteminden 2 tanesi" in v.headline


def test_bank_dcf_lens_ignores_any_dcf_result(cfg):
    # Bir DCF sonucu yanlışlıkla gelse bile banka için oy vermez.
    sc = DcfScenarioResult(scenario="base", assumptions={}, upside_vs_current_price=0.9)
    valuation = ValuationMetrics(pb_vs_history_ratio=1.4, history_years_used=4,
                                 dcf=DcfResult(bear=sc, base=sc, bull=sc))
    v = compute_verdict(valuation, _scores(50), 0.9, None, cfg,
                        dcf_not_applicable_reason=BANK_DCF_NOT_APPLICABLE_MESSAGE)
    assert _dcf_lens(v).verdict is None
    assert v.price == "PAHALI"
    assert v.confidence == "DUSUK"  # tek yöntem
    assert v.signal is None


def test_non_bank_dcf_lens_unchanged(cfg):
    v = compute_verdict(ValuationMetrics(), _scores(50), 0.9, None, cfg)
    dcf = _dcf_lens(v)
    assert dcf.not_applicable is False
    assert dcf.reason == "DCF hesaplanamadı."
    assert "verdict_lens_dcf" in v.missing_fields
