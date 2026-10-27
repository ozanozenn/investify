"""FastAPI lifespan: süreç ömrü boyunca yaşayan arka plan işleri.

Şimdilik tek iş izleme listesi zamanlayıcısı (ADR-013). Her uvicorn
worker'ı kendi zamanlayıcısını başlatır; aynı anda iki çalıştırmayı
`services/watchlist_refresh.py`'deki kilitler engeller.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.watchlist import REFRESH_TRIGGER_SCHEDULED
from app.services.provider_bundle import get_provider_bundle
from app.services.watchlist_refresh import refresh_runner
from app.services.watchlist_scheduler import RefreshSchedule, WatchlistScheduler

logger = get_logger(__name__)


def build_watchlist_scheduler(settings: Settings) -> WatchlistScheduler:
    async def job(slot: dt.datetime) -> None:
        await refresh_runner.run(
            SessionLocal,
            get_provider_bundle(),
            settings,
            trigger=REFRESH_TRIGGER_SCHEDULED,
            not_refreshed_since=slot,
        )

    # Geçersiz gün/saat ayarı açılışta hata verir (sessizce kapanmaz).
    return WatchlistScheduler(RefreshSchedule.from_settings(settings), job)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    scheduler: WatchlistScheduler | None = None
    if settings.watchlist_refresh_enabled:
        scheduler = build_watchlist_scheduler(settings)
        scheduler.start()
    else:
        logger.info("watchlist_scheduler_disabled")
    app.state.watchlist_scheduler = scheduler
    try:
        yield
    finally:
        if scheduler is not None:
            await scheduler.stop()
        await refresh_runner.cancel()
        app.state.watchlist_scheduler = None
