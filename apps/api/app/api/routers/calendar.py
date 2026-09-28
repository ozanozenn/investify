"""Yaklaşan önemli gelişmeler takvimi (Phase 4 "Takvim" sekmesi).

İki farklı güvenilirlik seviyesinde iki ayrı veri kümesi birleştirilir:
- TCMB faiz kararı tarihleri: gerçekten ileriye dönük, resmi ve kesin
  (`config/tcmb_calendar.yaml`, TCMB'nin kendi yayınladığı takvimden elle
  kopyalanmış).
- Şirket olayları (temettü / sermaye artırımı / halka arz): KAP'ın
  market-wide akışından, kategoriye göre filtrelenmiş, en son duyurular.
  Bunlar duyuru TARİHİDİR — şirketin ileride uygulayacağı kesin ödeme/kayıt
  tarihi değildir (o bilgi için KAP linkine yönlendiriyoruz). Bunu olduğu
  gibi (tahmin etmeden) sunmak, ADR-003'ün "asla veri uydurma" ilkesiyle
  tutarlı; V2'de KAP detay sayfaları template'e özel parse edilerek kesin
  tarihler eklenebilir (henüz yapılmadı, roadmap'te not edildi).
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_tcmb_calendar_config
from app.core.security import require_user
from app.models.enums import DisclosureCategory
from app.providers.base import ProviderUnavailableError
from app.providers.disclosure.kap_provider import KapDisclosureProvider
from app.schemas.calendar import CalendarResult, CompanyEvent, RateDecisionEvent

router = APIRouter(prefix="/api/calendar", tags=["calendar"], dependencies=[Depends(require_user)])

_disclosure_provider = KapDisclosureProvider()

_COMPANY_EVENT_CATEGORIES = {DisclosureCategory.DIVIDEND, DisclosureCategory.CAPITAL, DisclosureCategory.IPO}


@router.get("", response_model=CalendarResult)
async def get_calendar(
    upcoming_rate_decisions: int = 6,
    company_event_lookback_days: int = 14,
    company_event_limit: int = 30,
):
    today = dt.date.today()
    config = get_tcmb_calendar_config()
    rate_decisions = sorted(
        dt.date.fromisoformat(m["date"]) for m in config["meetings"] if dt.date.fromisoformat(m["date"]) >= today
    )[:upcoming_rate_decisions]

    try:
        raw_items = await _disclosure_provider.get_market_disclosures(
            lookback_days=company_event_lookback_days, limit=200
        )
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=f"Şirket olayları şu anda alınamıyor: {exc}") from exc

    company_events = sorted(
        (i for i in raw_items if i.category in _COMPANY_EVENT_CATEGORIES),
        key=lambda i: i.published_at,
        reverse=True,
    )[:company_event_limit]

    return CalendarResult(
        rate_decisions=[RateDecisionEvent(date=d) for d in rate_decisions],
        company_events=[
            CompanyEvent(
                ticker=i.ticker,
                company_name=i.company_name,
                category=i.category.value,
                title=i.title,
                announced_at=i.published_at,
                source_url=i.source_url,
            )
            for i in company_events
        ],
    )
