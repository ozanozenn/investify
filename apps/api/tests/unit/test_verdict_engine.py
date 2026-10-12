import copy

import pytest

from app.core.config import get_verdict_config
from app.schemas.dcf import DcfResult, DcfScenarioResult
from app.schemas.scoring import CategoryScore, ScoreResult
from app.schemas.valuation import ValuationMetrics
from app.verdict_engine.engine import PeerMedians, compute_verdict


def _scores(overall: float, unsupported: str | None = None) -> ScoreResult:
    cat = CategoryScore(label="x", score=overall, components=[])
    return ScoreResult(
        growth=cat, profitability=cat, balance_sheet=cat, cash_flow=cat, valuation=cat,
        overall=overall, overall_weights={}, engine_version="v1", unsupported_reason=unsupported,
    )


def _dcf(upside: float | None) -> DcfResult:
    def sc(name):
        return DcfScenarioResult(scenario=name, assumptions={}, upside_vs_current_price=upside)
    return DcfResult(bear=sc("bear"), base=sc("base"), bull=sc("bull"))


def _valuation(history_ratio: float | None = None, upside: float | None = None,
               pe: float | None = 10.0) -> ValuationMetrics:
    return ValuationMetrics(
        pe=pe, ev_ebitda=None, pb=None,
        pe_vs_history_ratio=history_ratio, history_years_used=5,
        dcf=_dcf(upside) if upside is not None else None,
    )


@pytest.fixture
def cfg():
    return copy.deepcopy(get_verdict_config())


def test_all_lenses_cheap_strong_company_is_al_with_high_confidence(cfg):
    v = compute_verdict(
        _valuation(history_ratio=0.7, upside=0.4, pe=8.0), _scores(72), 0.9,
        PeerMedians(peer_count=3, median_pe=12.0), cfg,
    )
    assert v.price == "UCUZ"
    assert v.quality == "GUCLU"
    assert v.confidence == "YUKSEK"
    assert v.agreement == 1.0
    assert v.signal == "AL"
    assert v.missing_fields == []
    assert "3 değerleme yönteminden 3 tanesi" in v.headline


def test_cheap_but_weak_company_is_not_al(cfg):
    # "Değer tuzağı": ucuz ama zayıf şirkete AL verilmez.
    v = compute_verdict(_valuation(history_ratio=0.6, upside=0.5), _scores(30), 0.9, None, cfg)
    assert v.price == "UCUZ"
    assert v.quality == "ZAYIF"
    assert v.signal == "TUT"


def test_expensive_medium_company_is_sat(cfg):
    v = compute_verdict(_valuation(history_ratio=1.4, upside=-0.4), _scores(50), 0.9, None, cfg)
    assert v.price == "PAHALI"
    assert v.signal == "SAT"


def test_missing_lenses_are_never_guessed(cfg):
    v = compute_verdict(_valuation(history_ratio=None, upside=None, pe=None), _scores(60), 0.9, None, cfg)
    assert v.price is None
    assert v.signal is None
    assert v.confidence == "DUSUK"
    assert set(v.missing_fields) >= {"verdict_lens_history", "verdict_lens_peers", "verdict_lens_dcf"}
    assert "yeterli değerleme verisi yok" in v.headline


def test_single_lens_gives_low_confidence(cfg):
    v = compute_verdict(_valuation(history_ratio=0.7), _scores(70), 0.95, None, cfg)
    assert v.price == "UCUZ"
    assert v.confidence == "DUSUK"


def test_opposing_lenses_say_so_and_have_low_confidence(cfg):
    # +1 ve -1: ortalama MAKUL ama hiçbir yöntem "makul" demedi.
    v = compute_verdict(_valuation(history_ratio=0.7, upside=-0.4), _scores(70), 0.9, None, cfg)
    assert v.price == "MAKUL"
    assert v.confidence == "DUSUK"
    assert "farklı yönleri" in v.headline


def test_too_few_peers_skips_peer_lens(cfg):
    v = compute_verdict(_valuation(history_ratio=1.0), _scores(70), 0.9,
                        PeerMedians(peer_count=1, median_pe=5.0), cfg)
    peers = next(lens for lens in v.lenses if lens.key == "peers")
    assert peers.verdict is None
    assert "(1)" in peers.reason


def test_negative_pe_is_excluded_from_peer_ratio(cfg):
    v = compute_verdict(_valuation(pe=-4.0), _scores(70), 0.9, PeerMedians(peer_count=3, median_pe=10.0), cfg)
    peers = next(lens for lens in v.lenses if lens.key == "peers")
    assert peers.verdict is None


def test_signal_can_be_disabled(cfg):
    cfg["signal"]["enabled"] = False
    v = compute_verdict(_valuation(history_ratio=0.7, upside=0.4), _scores(72), 0.9, None, cfg)
    assert v.price == "UCUZ"
    assert v.signal is None
    assert v.signal_is_demo is False


def test_unsupported_industry_returns_no_verdict(cfg):
    v = compute_verdict(_valuation(history_ratio=0.7), _scores(0, "banka"), 0.9, None, cfg,
                        unsupported_reason="banka")
    assert v.price is None and v.quality is None and v.signal is None
    assert v.unsupported_reason == "banka"


def test_two_of_three_lenses_win_the_vote(cfg):
    v = compute_verdict(
        _valuation(history_ratio=0.6, upside=-0.5, pe=4.0), _scores(70), 0.9,
        PeerMedians(peer_count=3, median_pe=10.0), cfg,
    )
    assert v.price == "UCUZ"
    assert "3 değerleme yönteminden 2 tanesi" in v.headline

