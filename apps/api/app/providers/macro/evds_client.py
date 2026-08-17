"""TCMB EVDS (Electronic Data Delivery System) REST client.

Official docs: https://evds2.tcmb.gov.tr/index.php?/evds/userGuide
Requires a free API key (`EVDS_API_KEY`, see docs/DATA_SOURCES.md — this
environment does not have one, so this client is implemented against the
documented contract but has not been exercised against a live key; verify
series codes once a key is available).

Series used (Phase 1 minimum: policy rate, CPI — roadmap section 3.8):
  TP.APIFON4  — CBRT weighted average cost of funding (de facto policy rate
                proxy since TCMB funds the market through multiple
                instruments rather than a single announced rate)
  TP.FG.J0    — CPI index (level); YoY % is computed client-side from the
                index to avoid depending on undocumented EVDS `formula=`
                codes.
"""

from __future__ import annotations

import datetime as dt

import httpx

from app.providers.base import ProviderUnavailableError

_BASE_URL = "https://evds2.tcmb.gov.tr/service/evds"

SERIES_CODES = {
    "policy_rate": "TP.APIFON4",
    "cpi_index": "TP.FG.J0",
}


class EvdsClient:
    code = "tcmb_evds"

    def __init__(self, api_key: str, timeout: float = 15.0):
        self._api_key = api_key
        self._timeout = timeout

    async def get_series(
        self, series_code: str, start: dt.date, end: dt.date
    ) -> list[tuple[dt.date, float]]:
        params = {
            "series": series_code,
            "startDate": start.strftime("%d-%m-%Y"),
            "endDate": end.strftime("%d-%m-%Y"),
            "type": "json",
            "key": self._api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(_BASE_URL, params=params)
                resp.raise_for_status()
                payload = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailableError(self.code, f"EVDS series {series_code} failed: {exc}") from exc

        items = payload.get("items", [])
        field = series_code.replace(".", "_")
        out: list[tuple[dt.date, float]] = []
        for item in items:
            raw_value = item.get(field)
            raw_date = item.get("Tarih")
            if raw_value in (None, "") or not raw_date:
                continue
            try:
                value = float(str(raw_value).replace(",", "."))
            except ValueError:
                continue
            parsed_date = _parse_evds_date(raw_date)
            if parsed_date is not None:
                out.append((parsed_date, value))
        if not out:
            raise ProviderUnavailableError(self.code, f"EVDS series {series_code} returned no usable rows")
        return out


def _parse_evds_date(raw: str) -> dt.date | None:
    for fmt in ("%d-%m-%Y", "%m-%Y"):
        try:
            parsed = dt.datetime.strptime(raw, fmt)
            if fmt == "%m-%Y":
                # Monthly series: EVDS reports "MM-YYYY"; use month start.
                return dt.date(parsed.year, parsed.month, 1)
            return parsed.date()
        except ValueError:
            continue
    return None
