from __future__ import annotations

import datetime as dt

from pydantic import BaseModel

from app.schemas.context import (
    CompanyContext,
    DataQuality,
    DisclosureContext,
    MacroSeriesPoint,
    MarketContext,
    SourceRef,
)
from app.schemas.financial import FinancialHistoryPoint, FinancialMetrics
from app.schemas.quality import QualityFlagsResult, RealGrowth
from app.schemas.scoring import ScoreResult
from app.schemas.valuation import ValuationMetrics
from app.schemas.verdict import Verdict


class CompanyAnalysisResponse(BaseModel):
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
    analysis: dict
    unsupported_reason: str | None = None
    verdict: Verdict | None = None
    quality_flags: QualityFlagsResult | None = None
    real_growth: RealGrowth | None = None
    versions: dict[str, str]
    stage_results: dict[str, str] | None = None


class CompanySearchResult(BaseModel):
    ticker: str
    name: str
    sector: str | None = None
    industry: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
