"""Market-wide news/disclosure feed (Phase 4 "Haberler" page). Unlike
`routers/news.py` and the analysis snapshot's own KAP list, these endpoints
are not scoped to a single ticker and require no prior analysis — they
aggregate across every BIST-listed company.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_user
from app.providers.base import ProviderUnavailableError
from app.providers.disclosure.kap_provider import KapDisclosureProvider
from app.providers.news.google_news_provider import GoogleNewsProvider
from app.schemas.news import (
    MarketDisclosureItem,
    MarketDisclosureResult,
    MarketNewsResult,
    NewsItem,
)

router = APIRouter(prefix="/api/market", tags=["market"], dependencies=[Depends(require_user)])

_disclosure_provider = KapDisclosureProvider()
_news_provider = GoogleNewsProvider()


@router.get("/disclosures", response_model=MarketDisclosureResult)
async def get_market_disclosures(limit: int = 30, lookback_days: int = 3):
    try:
        raw_items = await _disclosure_provider.get_market_disclosures(lookback_days=lookback_days, limit=limit)
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=f"KAP açıklamaları şu anda alınamıyor: {exc}") from exc

    return MarketDisclosureResult(
        items=[
            MarketDisclosureItem(
                ticker=i.ticker,
                company_name=i.company_name,
                title=i.title,
                subject=i.subject,
                category=i.category.value,
                published_at=i.published_at,
                source_url=i.source_url,
            )
            for i in raw_items
        ],
    )


@router.get("/news", response_model=MarketNewsResult)
async def get_market_news(limit: int = 20):
    try:
        raw_items = await _news_provider.get_market_news(limit=limit)
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=f"Haberler şu anda alınamıyor: {exc}") from exc

    return MarketNewsResult(
        items=[NewsItem(title=i.title, source=i.source, url=i.url, published_at=i.published_at) for i in raw_items],
    )
