from __future__ import annotations

import datetime as dt

from app.schemas.context import (
    CompanyContext,
    DataQuality,
    DisclosureContext,
    MacroSeriesPoint,
    MarketContext,
    SourceRef,
    StructuredAnalysisContext,
)
from app.schemas.financial import FinancialHistoryPoint, FinancialMetrics
from app.schemas.scoring import ScoreResult
from app.schemas.valuation import ValuationMetrics
from app.schemas.verdict import Verdict


def build_context(
    ticker: str,
    company: CompanyContext,
    market: MarketContext,
    metrics: FinancialMetrics,
    financial_history: list[FinancialHistoryPoint],
    valuation: ValuationMetrics,
    scores: ScoreResult,
    macro: list[MacroSeriesPoint],
    disclosures: list[DisclosureContext],
    data_quality: DataQuality,
    sources: list[SourceRef],
    unsupported_reason: str | None = None,
    next_rate_decision_date: dt.date | None = None,
    verdict: Verdict | None = None,
) -> StructuredAnalysisContext:
    """Assembles the ONLY object the LLM layer ever receives (ADR-003).
    Pure: no DB/provider access — everything is passed in already computed.
    """
    return StructuredAnalysisContext(
        ticker=ticker,
        as_of=dt.datetime.now(dt.timezone.utc),
        company=company,
        market=market,
        metrics=metrics,
        financial_history=financial_history,
        valuation=valuation,
        scores=scores,
        macro=macro,
        disclosures=disclosures,
        data_quality=data_quality,
        sources=sources,
        unsupported_reason=unsupported_reason,
        next_rate_decision_date=next_rate_decision_date,
        verdict=verdict,
    )
