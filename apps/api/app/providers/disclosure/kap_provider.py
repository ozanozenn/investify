"""Real KAP (kap.org.tr) disclosure provider — unofficial but public,
unauthenticated JSON API. See docs/DATA_SOURCES.md and ADR-002 for the
endpoint research and rationale.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import time

import httpx

from app.core.logging import get_logger
from app.models.enums import DisclosureCategory
from app.providers.base import DisclosureProvider, ProviderUnavailableError, RawDisclosure

logger = get_logger(__name__)

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
    ("sermaye", DisclosureCategory.CAPITAL),
    ("pay geri alım", DisclosureCategory.CAPITAL),
]


def categorize(subject: str | None) -> DisclosureCategory:
    if not subject:
        return DisclosureCategory.OTHER
    lowered = subject.lower()
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


def _parse_kap_datetime(raw: str | None) -> dt.datetime:
    if not raw:
        return dt.datetime.now(dt.timezone.utc)
    try:
        naive = dt.datetime.strptime(raw, "%d.%m.%Y %H:%M:%S")
    except ValueError:
        return dt.datetime.now(dt.timezone.utc)
    istanbul = dt.timezone(dt.timedelta(hours=3))
    return naive.replace(tzinfo=istanbul).astimezone(dt.timezone.utc)
