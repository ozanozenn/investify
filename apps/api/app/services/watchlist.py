"""İzleme listesi CRUD'u ve liste özetleri (ADR-013).

Ekleme, şirket rotalarıyla aynı çözümleme yolunu kullanır
(`company_bootstrap.get_or_create_company`): şirket DB'de varsa ağ çağrısı
yapılmaz, yoksa `CompanyDataProvider` ile doğrulanıp kaydedilir. Tam analiz
eklemede çalıştırılmaz — ilk snapshot, şirket sayfası açıldığında ya da bir
sonraki toplu yenilemede oluşur.
"""

from __future__ import annotations

import datetime as dt
import re

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import utcnow
from app.models.company import Company
from app.models.snapshots import AnalysisSnapshot
from app.models.watchlist import REFRESH_STATUS_FAILED, WatchlistItem
from app.providers.base import CompanyDataProvider, ProviderUnavailableError
from app.schemas.watchlist import WatchlistItemSummary, WatchlistVerdictSummary
from app.services.company_bootstrap import get_or_create_company

_TICKER_RE = re.compile(r"^[A-Z0-9]{2,20}$")


class InvalidTickerError(ValueError):
    pass


class CompanyNotFoundError(LookupError):
    pass


def normalize_ticker(raw: str) -> str:
    ticker = raw.strip().upper()
    if not _TICKER_RE.match(ticker):
        raise InvalidTickerError(ticker)
    return ticker


def as_utc(value: dt.datetime | None) -> dt.datetime | None:
    """SQLite saat dilimini saklamaz (testler); saklanan her zaman UTC'dir."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=dt.timezone.utc)


async def get_item(session: AsyncSession, ticker: str) -> WatchlistItem | None:
    result = await session.execute(select(WatchlistItem).where(WatchlistItem.ticker == ticker))
    return result.scalar_one_or_none()


async def list_items(session: AsyncSession) -> list[WatchlistItem]:
    result = await session.execute(select(WatchlistItem).order_by(WatchlistItem.added_at, WatchlistItem.id))
    return list(result.scalars().all())


async def add_item(
    session: AsyncSession, ticker: str, company_provider: CompanyDataProvider
) -> tuple[WatchlistItem, bool]:
    """(kayıt, yeni_mi) döner. Zaten listedeyse idempotent davranır."""
    existing = await get_item(session, ticker)
    if existing is not None:
        return existing, False

    try:
        company = await get_or_create_company(session, ticker, company_provider)
    except ProviderUnavailableError as exc:
        await session.rollback()
        raise CompanyNotFoundError(ticker) from exc

    item = WatchlistItem(company_id=company.id, ticker=ticker, added_at=utcnow())
    session.add(item)
    try:
        await session.commit()
    except IntegrityError:  # aynı anda iki ekleme — diğeri kazandı
        await session.rollback()
        existing = await get_item(session, ticker)
        if existing is None:
            raise
        return existing, False
    return item, True


async def remove_item(session: AsyncSession, ticker: str) -> bool:
    result = await session.execute(delete(WatchlistItem).where(WatchlistItem.ticker == ticker))
    await session.commit()
    return (result.rowcount or 0) > 0


def _overall_score(context: dict) -> float | None:
    scores = context.get("scores") or {}
    if scores.get("unsupported_reason") or context.get("unsupported_reason"):
        return None  # desteklenmeyen sektörde 0 puan yanıltıcı olur
    overall = scores.get("overall")
    return float(overall) if overall is not None else None


def _verdict_summary(context: dict) -> WatchlistVerdictSummary | None:
    verdict = context.get("verdict")
    if not verdict:
        return None  # ADR-011 öncesi snapshot
    return WatchlistVerdictSummary(
        price=verdict.get("price"),
        quality=verdict.get("quality"),
        confidence=verdict.get("confidence"),
        signal=verdict.get("signal"),
        signal_is_demo=bool(verdict.get("signal_is_demo", True)),
        headline=verdict.get("headline"),
        unsupported_reason=verdict.get("unsupported_reason"),
    )


async def _latest_snapshots(session: AsyncSession, ticker: str, limit: int = 2) -> list[AnalysisSnapshot]:
    result = await session.execute(
        select(AnalysisSnapshot)
        .where(AnalysisSnapshot.ticker == ticker)
        .order_by(AnalysisSnapshot.created_at.desc(), AnalysisSnapshot.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def build_item_summary(session: AsyncSession, item: WatchlistItem) -> WatchlistItemSummary:
    snapshots = await _latest_snapshots(session, item.ticker)
    summary = WatchlistItemSummary(
        ticker=item.ticker,
        name=item.ticker,
        added_at=as_utc(item.added_at),
        has_analysis=bool(snapshots),
        last_job_at=as_utc(item.last_refresh_at),
        last_job_status=item.last_refresh_status,
        last_job_trigger=item.last_refresh_trigger,
        last_job_error=item.last_refresh_error,
        last_job_failed=item.last_refresh_status == REFRESH_STATUS_FAILED,
    )

    if not snapshots:
        company = await session.get(Company, item.company_id)
        if company is not None:
            summary.name = company.name
        return summary

    latest = snapshots[0]
    ctx = latest.context_json or {}
    market = ctx.get("market") or {}
    summary.name = (ctx.get("company") or {}).get("name") or item.ticker
    summary.price = market.get("price")
    summary.currency = market.get("currency")
    summary.as_of = as_utc(latest.as_of)
    summary.overall_score = _overall_score(ctx)
    summary.verdict = _verdict_summary(ctx)
    summary.last_refreshed_at = as_utc(latest.created_at)

    if len(snapshots) > 1:
        summary.previous_overall_score = _overall_score(snapshots[1].context_json or {})
        if summary.overall_score is not None and summary.previous_overall_score is not None:
            summary.score_change = round(summary.overall_score - summary.previous_overall_score, 1)
    return summary


async def build_summaries(session: AsyncSession) -> list[WatchlistItemSummary]:
    # Tek kullanıcı, birkaç düzine hisse: hisse başına iki satırlık sorgu
    # yeterli; liste büyürse pencere fonksiyonlu tek sorguya geçilir.
    return [await build_item_summary(session, item) for item in await list_items(session)]
