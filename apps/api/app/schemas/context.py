from __future__ import annotations

import datetime as dt

from pydantic import BaseModel

from app.schemas.financial import FinancialHistoryPoint, FinancialMetrics
from app.schemas.scoring import ScoreResult
from app.schemas.valuation import ValuationMetrics
from app.schemas.verdict import Verdict


class CompanyContext(BaseModel):
    ticker: str
    name: str
    sector: str | None
    industry: str | None
    description: str | None = None
    is_financial_industry: bool = False


class MarketContext(BaseModel):
    price: float | None
    currency: str
    market_cap: float | None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    as_of: dt.datetime | None


class MacroSeriesPoint(BaseModel):
    code: str
    label: str
    value: float
    observation_date: dt.date
    is_mock: bool


class DisclosureContext(BaseModel):
    title: str
    category: str
    published_at: dt.datetime
    source_url: str


class DataQuality(BaseModel):
    completeness: float
    freshness: float
    metric_coverage: float
    overall: float
    warnings: list[str] = []


class SourceRef(BaseModel):
    field: str
    source: str
    source_url: str | None = None
    fetched_at: dt.datetime
    published_at: dt.datetime | None = None
    is_mock: bool = False


class StructuredAnalysisContext(BaseModel):
    """The ONLY thing the LLM ever sees (ADR-003). Every number in here is
    already computed by a deterministic engine — the LLM interprets, it
    never calculates."""

    ticker: str
    as_of: dt.datetime
    company: CompanyContext
    market: MarketContext
    metrics: FinancialMetrics
    financial_history: list[FinancialHistoryPoint]
    valuation: ValuationMetrics
    scores: ScoreResult
    macro: list[MacroSeriesPoint]
    disclosures: list[DisclosureContext]
    data_quality: DataQuality
    sources: list[SourceRef]
    unsupported_reason: str | None = None
    next_rate_decision_date: dt.date | None = None
    # Eski snapshot'larda yok (ADR-011'den önce) — bu yüzden opsiyonel.
    verdict: Verdict | None = None
