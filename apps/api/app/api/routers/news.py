"""General market/company news (Phase 4). Deliberately stateless: unlike
`/analysis`, this does not require a prior refresh or any DB row for the
ticker — news is independent of the financial-analysis pipeline, so a
ticker can be queried here even before it has ever been analyzed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_user
from app.providers.base import ProviderUnavailableError
from app.providers.news.google_news_provider import GoogleNewsProvider
from app.schemas.news import NewsItem, NewsResult

router = APIRouter(prefix="/api/companies", tags=["news"], dependencies=[Depends(require_user)])

_provider = GoogleNewsProvider()


@router.get("/{ticker}/news", response_model=NewsResult)
async def get_company_news(ticker: str, limit: int = 15):
    ticker = ticker.upper()
    try:
        raw_items = await _provider.get_news(ticker, limit=limit)
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=f"Haberler şu anda alınamıyor: {exc}") from exc

    return NewsResult(
        ticker=ticker,
        items=[
            NewsItem(title=i.title, source=i.source, url=i.url, published_at=i.published_at) for i in raw_items
        ],
    )
