"""Sayfa açılışında güncel fiyat (önbellekli), snapshot'tan bağımsız.

Akış: önbellek -> piyasa sağlayıcısı (`get_quote`) -> önbelleğe yaz.
Sağlayıcı başarısızsa son `AnalysisSnapshot`'taki fiyata düşülür ve açıkça
`stale=True` işaretlenir; bu yedek önbelleğe yazılmaz (bir sonraki istek
canlı fiyatı yeniden dener). Yeni snapshot oluşturulmaz (ADR-005).
"""

from __future__ import annotations

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.snapshots import AnalysisSnapshot
from app.providers.base import MarketDataProvider, ProviderUnavailableError, Quote
from app.schemas.quote import LiveQuote
from app.services.cache import JsonCache

logger = get_logger(__name__)

DELAY_NOTE = "Fiyatlar ~15 dk gecikmeli olabilir."
STALE_NOTE = "Güncel fiyat şu anda alınamıyor; son analizdeki fiyat gösteriliyor."
SNAPSHOT_SOURCE = "snapshot"

_CACHE_KEY = "quote:v1:{ticker}"


class QuoteUnavailableError(Exception):
    """Ne canlı fiyat ne de snapshot'ta kayıtlı bir fiyat var."""


def price_change(
    price: float, previous_close: float | None
) -> tuple[float | None, float | None, str | None]:
    """(değişim, kesir olarak değişim, yön). Önceki kapanış yoksa hepsi None."""
    if previous_close is None or previous_close <= 0:
        return None, None, None
    change = price - previous_close
    direction = "flat" if change == 0 else ("up" if change > 0 else "down")
    return change, price / previous_close - 1, direction


def _from_provider(quote: Quote) -> LiveQuote:
    change, change_fraction, direction = price_change(quote.price, quote.previous_close)
    return LiveQuote(
        ticker=quote.ticker.upper(),
        price=quote.price,
        currency=quote.currency,
        market_cap=quote.market_cap,
        as_of=quote.market_time or quote.as_of,
        source=quote.source_code,
        delay_note=DELAY_NOTE,
        previous_close=quote.previous_close,
        change=change,
        change_fraction=change_fraction,
        direction=direction,
    )


async def _snapshot_fallback(db: AsyncSession, ticker: str) -> LiveQuote | None:
    result = await db.execute(
        select(AnalysisSnapshot)
        .where(AnalysisSnapshot.ticker == ticker)
        .order_by(AnalysisSnapshot.created_at.desc())
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if snapshot is None:
        return None
    market = (snapshot.context_json or {}).get("market") or {}
    price = market.get("price")
    if price is None:
        return None
    return LiveQuote(
        ticker=ticker,
        price=price,
        currency=market.get("currency") or "TRY",
        market_cap=market.get("market_cap"),
        # context_json'da ISO metin; Pydantic datetime'a çevirir.
        as_of=market.get("as_of") or snapshot.as_of,
        source=SNAPSHOT_SOURCE,
        stale=True,
        delay_note=DELAY_NOTE,
        stale_note=STALE_NOTE,
    )


async def get_live_quote(
    db: AsyncSession,
    ticker: str,
    market: MarketDataProvider,
    cache: JsonCache,
    ttl_seconds: int,
) -> LiveQuote:
    ticker = ticker.upper()
    key = _CACHE_KEY.format(ticker=ticker)

    cached = await cache.get_json(key)
    if cached is not None:
        try:
            return LiveQuote.model_validate({**cached, "is_cached": True})
        except ValidationError:
            logger.warning("quote_cache_entry_invalid", extra={"ticker": ticker})

    try:
        quote = await market.get_quote(ticker)
    except ProviderUnavailableError as exc:
        logger.warning("live_quote_failed", extra={"ticker": ticker, "error": str(exc)})
        fallback = await _snapshot_fallback(db, ticker)
        if fallback is None:
            raise QuoteUnavailableError(
                f"{ticker} için güncel fiyat şu anda alınamıyor ve kayıtlı bir analiz de yok."
            ) from exc
        return fallback

    live = _from_provider(quote)
    await cache.set_json(key, live.model_dump(mode="json"), ttl_seconds)
    return live
