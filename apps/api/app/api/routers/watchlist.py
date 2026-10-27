"""İzleme listesi (ADR-013): ekle/çıkar, özet listesi ve toplu yenileme."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_db, get_providers, get_session_factory
from app.core.config import Settings, get_settings
from app.core.security import require_user
from app.models.watchlist import REFRESH_TRIGGER_MANUAL
from app.schemas.watchlist import (
    WatchlistAddRequest,
    WatchlistItemSummary,
    WatchlistRefreshStartResponse,
    WatchlistResponse,
    WatchlistSchedulerStatus,
)
from app.services.provider_bundle import ProviderBundle
from app.services.watchlist import (
    CompanyNotFoundError,
    InvalidTickerError,
    add_item,
    build_item_summary,
    build_summaries,
    list_items,
    normalize_ticker,
    remove_item,
)
from app.services.watchlist_refresh import refresh_runner
from app.services.watchlist_scheduler import RefreshSchedule, WatchlistScheduler

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"], dependencies=[Depends(require_user)])


def _scheduler_status(request: Request, settings: Settings) -> WatchlistSchedulerStatus:
    scheduler: WatchlistScheduler | None = getattr(request.app.state, "watchlist_scheduler", None)
    enabled = scheduler is not None and scheduler.is_running
    if scheduler is not None:
        label = scheduler.schedule.label()
    else:
        try:
            label = RefreshSchedule.from_settings(settings).label()
        except ValueError:
            label = "Geçersiz zamanlama ayarı"
    report = refresh_runner.last_report
    return WatchlistSchedulerStatus(
        enabled=enabled,
        schedule_label=label,
        next_run_at=scheduler.next_run_at if enabled else None,
        running=refresh_runner.running,
        last_run_trigger=report.trigger if report else None,
        last_run_started_at=report.started_at if report else None,
        last_run_finished_at=report.finished_at if report else None,
        last_run_succeeded=report.succeeded if report else None,
        last_run_failed=report.failed if report else None,
    )


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return WatchlistResponse(items=await build_summaries(db), scheduler=_scheduler_status(request, settings))


@router.post("", response_model=WatchlistItemSummary, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    body: WatchlistAddRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    providers: ProviderBundle = Depends(get_providers),
):
    """Zaten listedeyse 200 ile mevcut kaydı döner (idempotent)."""
    try:
        ticker = normalize_ticker(body.ticker)
    except InvalidTickerError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Geçersiz hisse kodu: '{body.ticker.strip()}'. Yalnızca harf ve rakam (2-20 karakter) kullanılabilir.",
        ) from exc
    try:
        item, created = await add_item(db, ticker, providers.company)
    except CompanyNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"{ticker} kodlu şirket bulunamadı ya da şu anda doğrulanamadı.",
        ) from exc
    if not created:
        response.status_code = status.HTTP_200_OK
    return await build_item_summary(db, item)


@router.delete("/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(ticker: str, db: AsyncSession = Depends(get_db)):
    symbol = ticker.strip().upper()
    if not await remove_item(db, symbol):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{symbol} izleme listende yok.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/refresh", response_model=WatchlistRefreshStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def refresh_watchlist_now(
    db: AsyncSession = Depends(get_db),
    providers: ProviderBundle = Depends(get_providers),
    settings: Settings = Depends(get_settings),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
):
    """Zamanlanmış işin aynısını hemen başlatır ve beklemeden döner (202).
    İlerleme `GET /api/watchlist` içindeki `scheduler.running` ile izlenir."""
    items = await list_items(db)
    if not items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="İzleme listen boş — önce hisse ekle.")
    if not refresh_runner.start_background(session_factory, providers, settings, trigger=REFRESH_TRIGGER_MANUAL):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="İzleme listesi yenilemesi zaten çalışıyor.")
    return WatchlistRefreshStartResponse(
        started=True,
        tickers=len(items),
        message=f"{len(items)} hisse arka planda yenileniyor.",
    )
