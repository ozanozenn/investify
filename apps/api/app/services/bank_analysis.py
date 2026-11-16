"""Banka analiz akışı (ADR-014): banka motoru + göreli değerleme + banka skoru.

`refresh_pipeline.py` bankalar için genel motor yerine bunu çağırır. I/O
yapmaz; sadece saf motorları birleştirir. DCF bankalara uygulanmaz
(`valuation.dcf` None kalır) ve FD/FAVÖK bankada anlamsız olduğu için
boşaltılır — böylece hüküm motorunun tarihsel/sektör yöntemleri yalnızca
F/K ve PD/DD ile oy verir.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.financial_engine.bank_engine import compute_bank_metrics
from app.providers.base import Candle, Quote
from app.schemas.bank import BankMetrics
from app.schemas.financial import FinancialMetrics, PeriodData
from app.schemas.scoring import ScoreResult
from app.schemas.valuation import ValuationMetrics
from app.scoring_engine.bank_scoring import compute_bank_score
from app.valuation_engine.engine import compute_valuation

# Genel `FinancialMetrics` bankada çoğunlukla anlamsız (FAVÖK, net borç,
# serbest nakit akışı); yalnızca tanımı aynı olan alanlar doldurulur.
GENERIC_METRICS_NOT_APPLICABLE = "generic_metrics_not_applicable_bank"
EV_EBITDA_NOT_APPLICABLE = "ev_ebitda_not_applicable_bank"
DCF_NOT_APPLICABLE = "dcf_not_applicable_bank"


@dataclass
class BankAnalysis:
    bank_metrics: BankMetrics
    metrics: FinancialMetrics
    valuation: ValuationMetrics
    scores: ScoreResult


def _bank_valuation(valuation: ValuationMetrics) -> ValuationMetrics:
    missing = [m for m in valuation.missing_fields if m != "ev_ebitda_unavailable"]
    return valuation.model_copy(
        update={
            "ev_ebitda": None,
            "ev_ebitda_historical_median": None,
            "ev_ebitda_vs_history_ratio": None,
            "dcf": None,
            "missing_fields": missing + [EV_EBITDA_NOT_APPLICABLE, DCF_NOT_APPLICABLE],
        }
    )


def analyze_bank(
    annual_periods: list[PeriodData],
    quote: Quote | None,
    candles: list[Candle],
    lookback_years: int,
) -> BankAnalysis:
    periods = sorted(annual_periods, key=lambda p: p.fiscal_year)
    bank_metrics = compute_bank_metrics(periods)

    valuation = _bank_valuation(
        compute_valuation(
            current_price=quote.price if quote else None,
            market_cap=quote.market_cap if quote else None,
            shares_outstanding=quote.shares_outstanding if quote else None,
            latest_period=periods[-1] if periods else None,
            historical_periods=periods,
            historical_candles=candles,
            lookback_years=lookback_years,
        )
    )

    score_inputs = {
        **bank_metrics.model_dump(),
        "pe_vs_history_ratio": valuation.pe_vs_history_ratio,
        "pb_vs_history_ratio": valuation.pb_vs_history_ratio,
    }
    scores = compute_bank_score(score_inputs)

    metrics = FinancialMetrics(
        as_of_period=bank_metrics.as_of_period,
        roe=bank_metrics.roe,
        net_income_growth_yoy=bank_metrics.net_income_growth_yoy,
        equity_ratio=bank_metrics.equity_to_assets,
        latest_net_income=bank_metrics.latest_net_income,
        missing_fields=[GENERIC_METRICS_NOT_APPLICABLE],
    )
    return BankAnalysis(bank_metrics=bank_metrics, metrics=metrics, valuation=valuation, scores=scores)
