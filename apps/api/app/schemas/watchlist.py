"""İzleme listesi API şemaları (ADR-013).

Özetteki her sayı ya son `AnalysisSnapshot`'tan aynen okunur ya da
(skor değişimi gibi) backend'de hesaplanır — frontend hesaplama yapmaz.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel

from app.schemas.verdict import ConfidenceLabel, PriceLabel, QualityLabel, SignalLabel

RefreshStatus = Literal["SUCCESS", "FAILED"]
RefreshTrigger = Literal["scheduled", "manual"]


class WatchlistAddRequest(BaseModel):
    ticker: str


class WatchlistVerdictSummary(BaseModel):
    """Hüküm kartının (ADR-011) liste için inceltilmiş hâli."""

    price: PriceLabel | None = None
    quality: QualityLabel | None = None
    confidence: ConfidenceLabel | None = None
    signal: SignalLabel | None = None
    signal_is_demo: bool = True
    headline: str | None = None
    unsupported_reason: str | None = None


class WatchlistItemSummary(BaseModel):
    ticker: str
    name: str
    added_at: dt.datetime
    has_analysis: bool

    # Son snapshot'tan
    price: float | None = None
    currency: str | None = None
    as_of: dt.datetime | None = None
    overall_score: float | None = None
    verdict: WatchlistVerdictSummary | None = None
    last_refreshed_at: dt.datetime | None = None

    # Bir önceki snapshot'a göre (yoksa None)
    previous_overall_score: float | None = None
    score_change: float | None = None

    # Son toplu yenileme işi (zamanlanmış ya da "Şimdi yenile")
    last_job_at: dt.datetime | None = None
    last_job_status: RefreshStatus | None = None
    last_job_trigger: RefreshTrigger | None = None
    last_job_error: str | None = None
    last_job_failed: bool = False


class WatchlistSchedulerStatus(BaseModel):
    enabled: bool
    schedule_label: str
    next_run_at: dt.datetime | None = None
    running: bool = False
    last_run_trigger: RefreshTrigger | None = None
    last_run_started_at: dt.datetime | None = None
    last_run_finished_at: dt.datetime | None = None
    last_run_succeeded: int | None = None
    last_run_failed: int | None = None


class WatchlistResponse(BaseModel):
    items: list[WatchlistItemSummary]
    scheduler: WatchlistSchedulerStatus


class WatchlistRefreshStartResponse(BaseModel):
    started: bool
    tickers: int
    message: str
