"""Real KAP (kap.org.tr) disclosure provider — unofficial but public,
unauthenticated JSON API. See docs/DATA_SOURCES.md and ADR-002 for the
endpoint research and rationale.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import time
from dataclasses import dataclass

import httpx

from app.core.logging import get_logger
from app.models.enums import DisclosureCategory
from app.providers.base import DisclosureProvider, ProviderUnavailableError, RawDisclosure

logger = get_logger(__name__)


@dataclass
class RawMarketDisclosure:
    """A KAP disclosure not scoped to a single ticker — used by the market-wide
    "Haberler" feed (Phase 4), distinct from `RawDisclosure` which is always
    fetched for one company as part of its analysis snapshot.
    """

    ticker: str | None
    company_name: str
    title: str
    subject: str | None
    category: DisclosureCategory
    kap_disclosure_index: int
    published_at: dt.datetime
    source_url: str
    fetched_at: dt.datetime

_BASE_URL = "https://www.kap.org.tr"
_HEADERS = {
    "Content-Type": "application/json",
    "Referer": f"{_BASE_URL}/tr/bildirim-sorgu",
    "User-Agent": "Mozilla/5.0 (compatible; InvestifyBot/0.1; +personal-research-use)",
}
_RATE_LIMIT_SECONDS = 0.5

_SUBJECT_CATEGORY_KEYWORDS: list[tuple[str, DisclosureCategory]] = [
    ("finansal rapor", DisclosureCategory.FINANCIAL_RESULT),
    ("finansal tablo", DisclosureCategory.FINANCIAL_RESULT),
    ("bağımsız denetim", DisclosureCategory.FINANCIAL_RESULT),
    ("kar payı", DisclosureCategory.DIVIDEND),
    ("temettü", DisclosureCategory.DIVIDEND),
    ("yatırım", DisclosureCategory.INVESTMENT),
    ("sözleşme", DisclosureCategory.CONTRACT),
    ("ihale", DisclosureCategory.CONTRACT),
    ("yönetim kurulu", DisclosureCategory.MANAGEMENT),
    ("genel müdür", DisclosureCategory.MANAGEMENT),
    ("sermaye artır", DisclosureCategory.CAPITAL),
    ("sermaye azalt", DisclosureCategory.CAPITAL),
    ("bedelli", DisclosureCategory.CAPITAL),
    ("bedelsiz", DisclosureCategory.CAPITAL),
    ("pay geri alım", DisclosureCategory.CAPITAL),
    ("halka arz", DisclosureCategory.IPO),
    ("izahname", DisclosureCategory.IPO),
    ("borsada işlem görmeye başla", DisclosureCategory.IPO),
]


def categorize(subject: str | None, extra_text: str | None = None) -> DisclosureCategory:
    """`subject` is often a generic regulatory template name (e.g. "Özel Durum
    Açıklaması (Genel)" for every ODA-class disclosure); the real signal is
    frequently only in the free-text summary/title instead — so callers
    should pass that as `extra_text` whenever they have it.
    """
    lowered = f"{subject or ''} {extra_text or ''}".lower()
    if not lowered.strip():
        return DisclosureCategory.OTHER
    for keyword, category in _SUBJECT_CATEGORY_KEYWORDS:
        if keyword in lowered:
            return category
    return DisclosureCategory.OTHER


class KapDisclosureProvider(DisclosureProvider):
    code = "kap"

    def __init__(self) -> None:
        self._last_request_ts = 0.0

    async def _throttled_client(self) -> httpx.AsyncClient:
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < _RATE_LIMIT_SECONDS:
            await asyncio.sleep(_RATE_LIMIT_SECONDS - elapsed)
        self._last_request_ts = time.monotonic()
        return httpx.AsyncClient(base_url=_BASE_URL, headers=_HEADERS, timeout=15.0)

    async def _resolve_member_oid(self, client: httpx.AsyncClient, ticker: str) -> str:
        resp = await client.get(f"/tr/api/member/filter/{ticker.upper()}")
        resp.raise_for_status()
        matches = resp.json()
        if not matches:
            raise ProviderUnavailableError(self.code, f"ticker {ticker} not found on KAP")
        return matches[0]["mkkMemberOid"]

    async def get_disclosures(
        self, ticker: str, lookback_days: int = 90, limit: int = 15
    ) -> list[RawDisclosure]:
        try:
            client = await self._throttled_client()
            async with client:
                member_oid = await self._resolve_member_oid(client, ticker)
                await asyncio.sleep(_RATE_LIMIT_SECONDS)
                to_date = dt.date.today()
                from_date = to_date - dt.timedelta(days=lookback_days)
                resp = await client.post(
                    "/tr/api/disclosure/members/byCriteria",
                    json={
                        "fromDate": from_date.isoformat(),
                        "toDate": to_date.isoformat(),
                        "mkkMemberOidList": [member_oid],
                        "subjectList": [],
                    },
                )
                resp.raise_for_status()
                raw = resp.json()
        except ProviderUnavailableError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailableError(self.code, f"get_disclosures({ticker}) failed: {exc}") from exc

        now = dt.datetime.now(dt.timezone.utc)
        disclosures: list[RawDisclosure] = []
        for item in raw[:limit]:
            index = item.get("disclosureIndex")
            if index is None:
                continue
            published = _parse_kap_datetime(item.get("publishDate"))
            title = item.get("kapTitle") or item.get("summary") or "KAP Disclosure"
            disclosures.append(
                RawDisclosure(
                    kap_disclosure_index=int(index),
                    title=str(item.get("summary") or title),
                    subject=item.get("subject"),
                    published_at=published,
                    source_url=f"{_BASE_URL}/tr/Bildirim/{index}",
                    fetched_at=now,
                )
            )
        return disclosures

    async def get_market_disclosures(
        self, lookback_days: int = 3, limit: int = 30
    ) -> list[RawMarketDisclosure]:
        """Market-wide feed across every KAP member (empty `mkkMemberOidList`
        returns the full stream, live-verified 2026-09-28) — independent of
        any single ticker, used by the "Haberler" page rather than a
        company's own analysis snapshot.
        """
        try:
            client = await self._throttled_client()
            async with client:
                to_date = dt.date.today()
                from_date = to_date - dt.timedelta(days=lookback_days)
                resp = await client.post(
                    "/tr/api/disclosure/members/byCriteria",
                    json={
                        "fromDate": from_date.isoformat(),
                        "toDate": to_date.isoformat(),
                        "mkkMemberOidList": [],
                        "subjectList": [],
                    },
                )
                resp.raise_for_status()
                raw = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailableError(self.code, f"get_market_disclosures failed: {exc}") from exc

        now = dt.datetime.now(dt.timezone.utc)
        disclosures: list[RawMarketDisclosure] = []
        for item in raw[:limit]:
            index = item.get("disclosureIndex")
            if index is None:
                continue
            stock_codes = item.get("stockCodes")
            ticker = stock_codes.split(",")[0].strip() if stock_codes else None
            subject = item.get("subject")
            disclosures.append(
                RawMarketDisclosure(
                    ticker=ticker,
                    company_name=str(item.get("kapTitle") or ticker or "—"),
                    title=str(item.get("summary") or subject or "KAP Bildirimi"),
                    subject=subject,
                    category=categorize(subject, item.get("summary")),
                    kap_disclosure_index=int(index),
                    published_at=_parse_kap_datetime(item.get("publishDate")),
                    source_url=f"{_BASE_URL}/tr/Bildirim/{index}",
                    fetched_at=now,
                )
            )
        return disclosures


def _parse_kap_datetime(raw: str | None) -> dt.datetime:
    if not raw:
        return dt.datetime.now(dt.timezone.utc)
    try:
        naive = dt.datetime.strptime(raw, "%d.%m.%Y %H:%M:%S")
    except ValueError:
        return dt.datetime.now(dt.timezone.utc)
    istanbul = dt.timezone(dt.timedelta(hours=3))
    return naive.replace(tzinfo=istanbul).astimezone(dt.timezone.utc)
