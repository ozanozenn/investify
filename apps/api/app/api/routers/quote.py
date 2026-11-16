"""Sayfa açılışında güncel fiyat: `GET /api/companies/{ticker}/quote`.

Ayrı router (companies.py'ye dokunmadan) — analiz snapshot'ı oluşturmaz,
yalnızca önbellekli canlı fiyat döner (bkz. `services/live_quote.py`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_providers
from app.core.config import Settings, get_settings
from app.core.security import require_user
from app.schemas.quote import LiveQuote
from app.services.cache import JsonCache, get_cache
from app.services.live_quote import QuoteUnavailableError, get_live_quote
from app.services.provider_bundle import ProviderBundle
from app.services.watchlist import InvalidTickerError, normalize_ticker

router = APIRouter(prefix="/api/companies", tags=["quote"], dependencies=[Depends(require_user)])


@router.get("/{ticker}/quote", response_model=LiveQuote)
async def get_company_quote(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    providers: ProviderBundle = Depends(get_providers),
    cache: JsonCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
):
    # Doğrulanmamış kod sağlayıcıya ve önbellek anahtarına gitmesin.
    try:
        ticker = normalize_ticker(ticker)
    except InvalidTickerError as exc:
        raise HTTPException(
            status_code=422, detail=f"Geçersiz hisse kodu: '{ticker.strip()}'. Yalnızca harf ve rakam kullanılabilir."
        ) from exc
    try:
        return await get_live_quote(
            db, ticker, providers.market, cache, settings.quote_cache_ttl_seconds
        )
    except QuoteUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
