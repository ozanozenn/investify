"""Google News RSS provider — general market/company news (Phase 4,
distinct from KAP official disclosures already covered in Phase 1).

No API key, no official terms-of-service issue for personal/research use
of the public RSS search endpoint (same "unofficial but public" posture
already accepted for KAP in ADR-002). Live-verified 2026-09-17: real,
Turkish-language, relevant results for a real BIST ticker query.

Known simplifications (Phase 4 MVP — not full roadmap scope):
- No sentiment scoring. No clustering beyond simple title-similarity
  dedup. Both are deferred; this ships a clean, deduplicated, real news
  feed first per the user's explicit "keep it minimal for now" direction
  (2026-09-17).
- `link` items point at Google's News redirect URL, not the resolved
  publisher URL — Google News RSS does not expose the direct link
  without following the redirect (an extra request per article we're not
  paying for a first pass); the redirect still lands on the real article.
"""

from __future__ import annotations

import datetime as dt
import email.utils
import re
from difflib import SequenceMatcher
from urllib.parse import quote
from xml.etree import ElementTree

import httpx

from app.providers.base import NewsProvider, ProviderUnavailableError, RawNewsItem

_BASE_URL = "https://news.google.com/rss/search"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; InvestifyBot/0.1; +personal-research-use)"}

# Titles come back as "<headline> - <source>"; the <source> tag already
# gives us the clean source name, so we strip the matching suffix rather
# than displaying it twice.
_TITLE_SOURCE_SUFFIX_RE = re.compile(r"\s+-\s+[^-]+$")

_DEDUP_SIMILARITY_THRESHOLD = 0.75


class GoogleNewsProvider(NewsProvider):
    code = "google_news"

    def __init__(self, timeout: float = 15.0):
        self._timeout = timeout

    async def get_news(self, ticker: str, company_name: str | None = None, limit: int = 15) -> list[RawNewsItem]:
        return await self._search(f"{ticker.upper()} hisse", limit, error_context=f"get_news({ticker})")

    async def get_market_news(self, limit: int = 20) -> list[RawNewsItem]:
        """General BIST/market news, not scoped to one company — used by the
        market-wide "Haberler" page (Phase 4)."""
        return await self._search("Borsa İstanbul", limit, error_context="get_market_news")

    async def _search(self, query: str, limit: int, error_context: str) -> list[RawNewsItem]:
        url = f"{_BASE_URL}?q={quote(query)}&hl=tr&gl=TR&ceid=TR:tr"
        try:
            async with httpx.AsyncClient(timeout=self._timeout, headers=_HEADERS) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                root = ElementTree.fromstring(resp.text)
        except (httpx.HTTPError, ElementTree.ParseError) as exc:
            raise ProviderUnavailableError(self.code, f"{error_context} failed: {exc}") from exc

        now = dt.datetime.now(dt.timezone.utc)
        items: list[RawNewsItem] = []
        seen_titles: list[str] = []
        for item in root.iterfind(".//item"):
            title_el = item.findtext("title")
            link_el = item.findtext("link")
            pub_el = item.findtext("pubDate")
            source_el = item.find("source")
            if not title_el or not link_el:
                continue

            source_name = (source_el.text or "").strip() if source_el is not None else ""
            clean_title = _TITLE_SOURCE_SUFFIX_RE.sub("", title_el).strip() if source_name else title_el.strip()

            if _is_near_duplicate(clean_title, seen_titles):
                continue
            seen_titles.append(clean_title)

            items.append(
                RawNewsItem(
                    title=clean_title,
                    source=source_name or "Google Haberler",
                    url=link_el.strip(),
                    published_at=_parse_rss_date(pub_el) or now,
                    fetched_at=now,
                )
            )
            if len(items) >= limit:
                break

        return items


def _is_near_duplicate(title: str, seen: list[str]) -> bool:
    normalized = title.lower()
    return any(SequenceMatcher(None, normalized, s.lower()).ratio() >= _DEDUP_SIMILARITY_THRESHOLD for s in seen)


def _parse_rss_date(raw: str | None) -> dt.datetime | None:
    if not raw:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)
