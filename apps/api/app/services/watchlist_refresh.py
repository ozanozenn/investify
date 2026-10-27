"""İzleme listesini toplu yenileyen iş (ADR-013).

Hem zamanlayıcı (`services/watchlist_scheduler.py`) hem de
`POST /api/watchlist/refresh` aynı `WatchlistRefreshRunner.run`'ı çağırır.

- Hisseler sırayla yenilenir; her biri kendi `AsyncSession`'ını açar
  (`run_refresh` tek oturumla çalışacak şekilde yazıldı).
- Bir hissenin hatası diğerlerini durdurmaz; sonuç (SUCCESS/FAILED, hata
  metni, zaman, tetikleyici) `watchlist_items` satırına yazılır.
- Aynı süreçte üst üste binen çalıştırmaları `asyncio.Lock`, birden fazla
  uvicorn worker'ı / süreç arasında ise PostgreSQL advisory lock engeller
  (SQLite'ta — testlerde — yalnızca süreç içi kilit vardır).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.base import utcnow
from app.models.watchlist import (
    REFRESH_STATUS_FAILED,
    REFRESH_STATUS_SUCCESS,
    WatchlistItem,
)
from app.services.provider_bundle import ProviderBundle
from app.services.refresh_pipeline import run_refresh
from app.services.watchlist import as_utc

logger = get_logger(__name__)

# pg_try_advisory_lock anahtarı — veritabanında bu işe ayrılmış sabit bir sayı.
_ADVISORY_LOCK_KEY = 7_013_000_013
_MAX_ERROR_LENGTH = 500

SessionFactory = async_sessionmaker[AsyncSession]


@dataclass
class TickerRefreshOutcome:
    ticker: str
    status: str
    error: str | None = None


@dataclass
class WatchlistRefreshReport:
    trigger: str
    started_at: dt.datetime
    finished_at: dt.datetime | None = None
    outcomes: list[TickerRefreshOutcome] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return sum(1 for o in self.outcomes if o.status == REFRESH_STATUS_SUCCESS)

    @property
    def failed(self) -> int:
        return sum(1 for o in self.outcomes if o.status == REFRESH_STATUS_FAILED)


async def _refresh_one(
    session_factory: SessionFactory,
    ticker: str,
    providers: ProviderBundle,
    settings: Settings,
    trigger: str,
) -> TickerRefreshOutcome:
    try:
        async with session_factory() as session:
            await run_refresh(
                session, ticker, providers, settings, request_id=f"watchlist-{trigger}-{uuid.uuid4()}"
            )
        return TickerRefreshOutcome(ticker=ticker, status=REFRESH_STATUS_SUCCESS)
    except Exception as exc:  # bir hissenin hatası diğerlerini durdurmamalı
        message = (str(exc) or type(exc).__name__)[:_MAX_ERROR_LENGTH]
        logger.warning("watchlist_ticker_refresh_failed", extra={"ticker": ticker, "error": message})
        return TickerRefreshOutcome(ticker=ticker, status=REFRESH_STATUS_FAILED, error=message)


async def _record_outcome(session_factory: SessionFactory, outcome: TickerRefreshOutcome, trigger: str) -> None:
    async with session_factory() as session:
        # Satır iş sürerken listeden silinmişse 0 satır güncellenir; sorun değil.
        await session.execute(
            update(WatchlistItem)
            .where(WatchlistItem.ticker == outcome.ticker)
            .values(
                last_refresh_at=utcnow(),
                last_refresh_status=outcome.status,
                last_refresh_trigger=trigger,
                last_refresh_error=outcome.error,
            )
        )
        await session.commit()


async def refresh_watchlist(
    session_factory: SessionFactory,
    providers: ProviderBundle,
    settings: Settings,
    *,
    trigger: str,
    not_refreshed_since: dt.datetime | None = None,
) -> WatchlistRefreshReport:
    """Listedeki tüm hisseleri sırayla yeniler.

    `not_refreshed_since` verilirse, son toplu yenilemesi bu andan sonra
    olan hisseler atlanır. Zamanlayıcı bunu çalıştığı zaman dilimiyle
    çağırır: aynı dilimi ikinci bir worker yakalarsa iş tekrarlanmaz.
    """
    report = WatchlistRefreshReport(trigger=trigger, started_at=utcnow())
    async with session_factory() as session:
        rows = (
            await session.execute(
                select(WatchlistItem.ticker, WatchlistItem.last_refresh_at).order_by(
                    WatchlistItem.added_at, WatchlistItem.id
                )
            )
        ).all()

    for ticker, last_refresh_at in rows:
        last = as_utc(last_refresh_at)
        if not_refreshed_since is not None and last is not None and last >= not_refreshed_since:
            report.skipped.append(ticker)
            continue
        outcome = await _refresh_one(session_factory, ticker, providers, settings, trigger)
        await _record_outcome(session_factory, outcome, trigger)
        report.outcomes.append(outcome)

    report.finished_at = utcnow()
    logger.info(
        "watchlist_refresh_finished",
        extra={
            "trigger": trigger,
            "succeeded": report.succeeded,
            "failed": report.failed,
            "skipped": len(report.skipped),
        },
    )
    return report


@asynccontextmanager
async def _cross_process_guard(session_factory: SessionFactory) -> AsyncIterator[bool]:
    """PostgreSQL'de oturum düzeyinde advisory lock. Kilit bu oturumun
    bağlantısına bağlıdır; bu yüzden iş bitene kadar commit edilmez (commit
    bağlantıyı havuza geri verirdi). Süreç ölürse bağlantıyla birlikte
    kilit de düşer."""
    async with session_factory() as session:
        if session.get_bind().dialect.name != "postgresql":
            yield True
            return
        acquired = bool(
            (await session.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": _ADVISORY_LOCK_KEY})).scalar()
        )
        try:
            yield acquired
        finally:
            if acquired:
                await session.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _ADVISORY_LOCK_KEY})


class WatchlistRefreshRunner:
    """Süreç içi tekil çalıştırıcı + son çalıştırmanın durumu (UI için).

    Durum bellekte tutulur; yeniden başlatmada kaybolur. Hisse bazındaki
    kalıcı sonuç zaten `watchlist_items` tablosundadır.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self.current_trigger: str | None = None
        self.current_started_at: dt.datetime | None = None
        self.last_report: WatchlistRefreshReport | None = None

    @property
    def running(self) -> bool:
        return self._lock.locked() or (self._task is not None and not self._task.done())

    async def run(
        self,
        session_factory: SessionFactory,
        providers: ProviderBundle,
        settings: Settings,
        *,
        trigger: str,
        not_refreshed_since: dt.datetime | None = None,
    ) -> WatchlistRefreshReport | None:
        """Raporu döner; başka bir çalıştırma sürüyorsa None."""
        if self._lock.locked():
            logger.info("watchlist_refresh_skipped_already_running", extra={"trigger": trigger})
            return None
        async with self._lock:
            self.current_trigger, self.current_started_at = trigger, utcnow()
            try:
                async with _cross_process_guard(session_factory) as acquired:
                    if not acquired:
                        logger.info("watchlist_refresh_skipped_other_process", extra={"trigger": trigger})
                        return None
                    report = await refresh_watchlist(
                        session_factory,
                        providers,
                        settings,
                        trigger=trigger,
                        not_refreshed_since=not_refreshed_since,
                    )
                self.last_report = report
                return report
            finally:
                self.current_trigger, self.current_started_at = None, None

    def start_background(
        self,
        session_factory: SessionFactory,
        providers: ProviderBundle,
        settings: Settings,
        *,
        trigger: str,
    ) -> bool:
        """İşi arka planda başlatır; zaten çalışıyorsa False."""
        if self.running:
            return False
        self._task = asyncio.create_task(
            self._run_logged(session_factory, providers, settings, trigger=trigger),
            name="watchlist-refresh",
        )
        return True

    async def _run_logged(self, *args, **kwargs) -> WatchlistRefreshReport | None:
        try:
            return await self.run(*args, **kwargs)
        except Exception:
            logger.exception("watchlist_refresh_crashed")
            return None

    async def wait(self) -> None:
        """Arka plandaki işin bitmesini bekler (testler ve kapanış için)."""
        if self._task is not None:
            await asyncio.shield(self._task)

    async def cancel(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


refresh_runner = WatchlistRefreshRunner()
