"""TCMB EVDS (Electronic Data Delivery System) REST client.

Official docs (EVDS3, obtained directly from the user 2026-09-17):
"EVDS Web Servis ve API Kullanımı" and "EVDS Python Kılavuzu", both from
evds3.tcmb.gov.tr. Requires a free API key (`EVDS_API_KEY`, see
docs/DATA_SOURCES.md).

TCMB has since migrated EVDS2 to a new platform ("EVDS3"), live-verified
2026-09-17 against a real key — every detail below is confirmed by the
official docs (initially reverse-engineered against
https://github.com/fatihmete/evds, a community client already adapted
for EVDS3, then cross-checked against the official PDFs). Several things
changed from the EVDS2 contract this client was originally written
against:
1. The endpoint moved from `evds2.tcmb.gov.tr/service/evds` to
   `evds3.tcmb.gov.tr/igmevdsms-dis/` — the old path now serves EVDS3's
   web app HTML at that path (not a clean redirect to a new API path, so
   simply following redirects was not enough).
2. The API key is now sent as an HTTP header (`key: <api_key>`), not a
   `key=` query parameter.
3. The query string is NOT a standard `?key=value&...` string — the
   server expects `key=value&...` appended directly to the base URL with
   no `?`, i.e. as a literal path suffix (verified live: the standard
   `?`-prefixed form 404s, the path-suffix form returns 200 with data).
   `httpx`'s own `params=` kwarg always adds the `?`, so this is built as
   a plain string instead.
4. Monthly series (e.g. CPI) now report dates as `"YYYY-M"` (e.g.
   `"2025-8"`, not zero-padded) rather than EVDS2's `"MM-YYYY"`.
The response body shape (`{"items": [...]}`, one dict per date with a
`SERIES_CODE_WITH_UNDERSCORES` value field and a `Tarih` date field) is
otherwise unchanged.

Two more details from the official docs, both already accounted for
elsewhere: `macro_provider.py` passes a far-future `endDate` (TCMB's own
documented recommendation, so freshness never depends on this server's
clock matching TCMB's actual publishing cadence — see
`_FAR_FUTURE_END_DATE`); a single request caps at 1000 observations
(counted back from `endDate`), which every call this client makes is
comfortably under.

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

_BASE_URL = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"

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
        query = (
            f"series={series_code}"
            f"&startDate={start.strftime('%d-%m-%Y')}"
            f"&endDate={end.strftime('%d-%m-%Y')}"
            "&type=json"
        )
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                resp = await client.get(_BASE_URL + query, headers={"key": self._api_key})
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
    for fmt in ("%d-%m-%Y", "%Y-%m", "%m-%Y"):
        try:
            parsed = dt.datetime.strptime(raw, fmt)
            if fmt in ("%Y-%m", "%m-%Y"):
                # Monthly series report a bare year-month (EVDS3: "YYYY-M",
                # not zero-padded; EVDS2 legacy: "MM-YYYY") — use month start.
                return dt.date(parsed.year, parsed.month, 1)
            return parsed.date()
        except ValueError:
            continue
    return None
