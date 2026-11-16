"""İş Yatırım financial statements provider (ADR-015).

İş Yatırım's website serves KAP-based Turkish financial statements as JSON
through an unauthenticated, undocumented endpoint used by its own "şirket
kartı" pages (and by open-source clients such as borsapy, isyatirimhisse
and borsa-mcp):

    GET https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo
        ?companyCode=THYAO&exchange=TRY&financialGroup=XI_29
        &year1=2025&period1=3&year2=2025&period2=6
        &year3=2025&period3=9&year4=2025&period4=12

    -> {"ok": true, "errorCode": null, "errorDescription": null,
        "value": [{"itemCode": "1BL", "itemDescTr": "TOPLAM VARLIKLAR",
                   "itemDescEng": "TOTAL ASSETS",
                   "value1": "2360037000000", "value2": ..., "value3": ..., "value4": ...},
                  ...]}

- Exactly four (year, period) pairs per request (clients report fewer
  returns empty values); `valueN` belongs to `yearN/periodN`, the response
  carries no period labels. `period` is the quarter-end month (3/6/9/12).
- Values are TRY in full units (exchange=TRY), as numeric strings or null.
- An empty `value` list means wrong financialGroup, unknown ticker or not
  yet published — the endpoint does not distinguish these.
- Income-statement/cash-flow items are cumulative YTD (see
  `isyatirim_mapping.py`); this provider converts quarters to single-quarter
  values so its output matches `YFinanceFinancialDataProvider`'s semantics.

**Not live-verified yet** (the build environment could not reach
isyatirim.com.tr). The provider is therefore disabled by default
(`FINANCIAL_PROVIDER_PRIMARY=yfinance`, no fallback) until the owner runs
`scripts/verify_isyatirim.py`. Licensing: the open-source clients state
personal/educational use only — fine for this single-user tool, a license
is needed if Investify ever becomes commercial (ADR-015).
"""

from __future__ import annotations

import asyncio
import calendar
import datetime as dt
from collections.abc import Callable

import httpx

from app.core.logging import get_logger
from app.providers.base import FinancialDataProvider, ProviderUnavailableError, RawFinancialPeriod
from app.providers.financial.isyatirim_mapping import (
    PRESENCE_ITEM_CODE,
    XI29_FINANCIAL_GROUP,
    discrete_quarter_values,
    parse_item_value,
    resolve_period,
)

logger = get_logger(__name__)

BASE_URL = "https://www.isyatirim.com.tr"
MALI_TABLO_PATH = "/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo"
COMPANY_PAGE_URL = f"{BASE_URL}/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx"

# The endpoint requires exactly four (year, period) pairs per request; one
# request per fiscal year fetches all four cumulative quarter-ends.
_PERIODS: tuple[int, int, int, int] = (3, 6, 9, 12)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; InvestifyBot/0.1; +personal-research-use)",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

PeriodKey = tuple[int, int]  # (year, period month)


def extract_rows(payload: object) -> list[dict]:
    """Validate the MaliTablo envelope and return its statement rows."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if not isinstance(payload, dict):
        raise ProviderUnavailableError("isyatirim", "unexpected MaliTablo response shape")
    if payload.get("ok") is False:
        detail = payload.get("errorDescription") or payload.get("errorCode") or "ok=false"
        raise ProviderUnavailableError("isyatirim", f"MaliTablo error: {detail}")
    rows = payload.get("value")
    if rows is None:
        raise ProviderUnavailableError("isyatirim", "MaliTablo response has no 'value' list")
    if not isinstance(rows, list):
        raise ProviderUnavailableError("isyatirim", "MaliTablo 'value' is not a list")
    return [r for r in rows if isinstance(r, dict)]


def parse_year_rows(
    rows: list[dict], year: int, periods: tuple[int, ...] = _PERIODS
) -> dict[PeriodKey, dict[str, float]]:
    """{(year, period): {itemCode: value}} for every period that is actually
    reported (total assets present and non-zero)."""
    out: dict[PeriodKey, dict[str, float]] = {}
    for index, period in enumerate(periods, start=1):
        items: dict[str, float] = {}
        for row in rows:
            code = str(row.get("itemCode") or "").strip()
            if not code or code in items:
                continue
            value = parse_item_value(row.get(f"value{index}"))
            if value is not None:
                items[code] = value
        if items.get(PRESENCE_ITEM_CODE):
            out[(year, period)] = items
    return out


def _period_end(year: int, month: int) -> dt.date:
    return dt.date(year, month, calendar.monthrange(year, month)[1])


def build_periods(
    cumulative: dict[PeriodKey, dict[str, float]],
    annual_years: int,
    quarterly_quarters: int,
    source_code: str,
    fetched_at: dt.datetime,
) -> list[RawFinancialPeriod]:
    """Turn cumulative per-period item values into canonical
    `RawFinancialPeriod`s: newest ANNUAL first, then newest QUARTERLY first
    (same ordering as the yfinance provider)."""
    resolved = {key: resolve_period(items) for key, items in cumulative.items()}
    out: list[RawFinancialPeriod] = []

    annual_keys = sorted((k for k in resolved if k[1] == 12), reverse=True)[:annual_years]
    for year, month in annual_keys:
        values = {field: rv.value for field, rv in resolved[(year, month)].items()}
        if not values:
            continue
        out.append(
            RawFinancialPeriod(
                period_type="ANNUAL",
                fiscal_year=year,
                fiscal_quarter=None,
                period_end_date=_period_end(year, month),
                currency="TRY",
                values=values,
                source_code=source_code,
                fetched_at=fetched_at,
            )
        )

    for year, month in sorted(resolved, reverse=True)[:quarterly_quarters]:
        quarter = month // 3
        previous = resolved.get((year, month - 3)) if quarter > 1 else None
        values = discrete_quarter_values(resolved[(year, month)], previous, quarter)
        if not values:
            continue
        out.append(
            RawFinancialPeriod(
                period_type="QUARTERLY",
                fiscal_year=year,
                fiscal_quarter=quarter,
                period_end_date=_period_end(year, month),
                currency="TRY",
                values=values,
                source_code=source_code,
                fetched_at=fetched_at,
            )
        )
    return out


class IsYatirimFinancialDataProvider(FinancialDataProvider):
    code = "isyatirim"

    def __init__(
        self,
        timeout_seconds: float = 20.0,
        request_interval_seconds: float = 0.3,
        today: Callable[[], dt.date] = dt.date.today,
    ) -> None:
        self._timeout = timeout_seconds
        self._interval = request_interval_seconds
        self._today = today

    def _client(self, symbol: str) -> httpx.AsyncClient:
        headers = {**_HEADERS, "Referer": f"{COMPANY_PAGE_URL}?hisse={symbol}"}
        return httpx.AsyncClient(base_url=BASE_URL, headers=headers, timeout=self._timeout)

    async def _fetch_year_rows(self, client: httpx.AsyncClient, symbol: str, year: int) -> list[dict]:
        params: dict[str, str | int] = {
            "companyCode": symbol,
            "exchange": "TRY",
            "financialGroup": XI29_FINANCIAL_GROUP,
        }
        for index, period in enumerate(_PERIODS, start=1):
            params[f"year{index}"] = year
            params[f"period{index}"] = period
        response = await client.get(MALI_TABLO_PATH, params=params)
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            # An HTML/empty body with HTTP 200 is how a soft block looks.
            raise ProviderUnavailableError(self.code, f"non-JSON MaliTablo response for {symbol}/{year}") from exc
        return extract_rows(payload)

    async def fetch_raw_rows(self, ticker: str, year: int) -> list[dict]:
        """Raw MaliTablo rows for one fiscal year (used by the verification
        script to show live itemCode -> itemDescTr labels)."""
        symbol = ticker.upper()
        async with self._client(symbol) as client:
            return await self._fetch_year_rows(client, symbol, year)

    async def get_financial_statements(
        self, ticker: str, annual_years: int = 5, quarterly_quarters: int = 8
    ) -> list[RawFinancialPeriod]:
        try:
            return await self._get_statements(ticker.upper(), annual_years, quarterly_quarters)
        except ProviderUnavailableError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError(
                self.code, f"get_financial_statements({ticker}) failed: {exc}"
            ) from exc

    async def _get_statements(
        self, symbol: str, annual_years: int, quarterly_quarters: int
    ) -> list[RawFinancialPeriod]:
        current_year = self._today().year
        # Current year (may be partly published) + enough past years for the
        # annual history and the quarterly window (incl. the quarter before
        # the oldest one, needed for YTD differencing).
        year_count = max(annual_years + 1, quarterly_quarters // 4 + 2)
        cumulative: dict[PeriodKey, dict[str, float]] = {}
        empty_years = 0
        async with self._client(symbol) as client:
            for i, year in enumerate(range(current_year, current_year - year_count, -1)):
                if i and self._interval:
                    await asyncio.sleep(self._interval)
                parsed = parse_year_rows(await self._fetch_year_rows(client, symbol, year), year)
                if parsed:
                    cumulative.update(parsed)
                    continue
                empty_years += 1
                if cumulative and year < current_year:
                    break  # history ends here (e.g. listed recently); stop asking
                if empty_years >= 2 and not cumulative:
                    break  # nothing for this year and last: not an XI_29 company
        if not cumulative:
            raise ProviderUnavailableError(
                self.code,
                f"no XI_29 statements for {symbol} (bank/insurer template, unknown code or unpublished)",
            )
        periods = build_periods(
            cumulative, annual_years, quarterly_quarters, self.code, dt.datetime.now(dt.timezone.utc)
        )
        if not periods:
            raise ProviderUnavailableError(self.code, f"no mappable statement lines for {symbol}")
        return periods
