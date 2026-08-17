from __future__ import annotations

import datetime as dt

from app.core.logging import get_logger
from app.providers.base import MacroDataProvider, MacroObservationDTO, ProviderUnavailableError
from app.providers.macro.evds_client import SERIES_CODES, EvdsClient
from app.providers.market.yfinance_provider import YFinanceFxProvider

logger = get_logger(__name__)

# Explicitly-labeled fallback used only when EVDS_API_KEY is not configured
# (roadmap section 92: mock fallback, never presented as production data).
# Values are a static snapshot recorded 2026-08-17 and WILL go stale; the
# `is_mock=True` flag is what protects the user from being misled — see
# docs/DATA_SOURCES.md.
_MOCK_SEED = {
    "policy_rate": 46.0,  # CBRT weighted avg funding cost, approx level mid-2026
    "cpi_yoy": 33.5,  # TÜİK CPI YoY %, approx level mid-2026
}
_MOCK_SEED_AS_OF = dt.date(2026, 8, 1)


class CompositeMacroDataProvider(MacroDataProvider):
    """Policy rate & CPI via TCMB EVDS (or labeled mock fallback); FX via
    Yahoo Finance (always real, no key required)."""

    code = "tcmb_evds+yfinance_fx"

    def __init__(self, evds_api_key: str | None):
        self._evds = EvdsClient(evds_api_key) if evds_api_key else None
        self._fx = YFinanceFxProvider()

    async def get_series(self, series_code: str, lookback_days: int = 400) -> list[MacroObservationDTO]:
        now = dt.datetime.now(dt.timezone.utc)
        if series_code in ("usdtry", "eurtry"):
            return await self._get_fx_series(series_code, now)
        if series_code in ("policy_rate", "cpi_yoy"):
            if self._evds is not None:
                try:
                    return await self._get_evds_series(series_code, lookback_days, now)
                except ProviderUnavailableError as exc:
                    logger.warning(
                        "evds_fetch_failed_falling_back_to_mock",
                        extra={"series": series_code, "error": str(exc)},
                    )
            return self._get_mock_series(series_code, now)
        raise ProviderUnavailableError(self.code, f"unknown macro series {series_code}")

    async def _get_fx_series(self, series_code: str, now: dt.datetime) -> list[MacroObservationDTO]:
        pair = "USDTRY" if series_code == "usdtry" else "EURTRY"
        rate = await self._fx.get_rate(pair)
        if rate is None:
            raise ProviderUnavailableError(self.code, f"fx rate unavailable for {pair}")
        return [
            MacroObservationDTO(
                series_code=series_code,
                observation_date=now.date(),
                value=rate,
                is_mock=False,
                fetched_at=now,
            )
        ]

    async def _get_evds_series(
        self, series_code: str, lookback_days: int, now: dt.datetime
    ) -> list[MacroObservationDTO]:
        assert self._evds is not None
        end = now.date()
        start = end - dt.timedelta(days=max(lookback_days, 400))  # extra buffer for YoY calc
        if series_code == "policy_rate":
            rows = await self._evds.get_series(SERIES_CODES["policy_rate"], start, end)
            date, value = rows[-1]
            return [
                MacroObservationDTO(
                    series_code=series_code, observation_date=date, value=value, is_mock=False, fetched_at=now
                )
            ]
        # cpi_yoy: derive from the CPI index (avoids relying on EVDS `formula=` codes)
        rows = await self._evds.get_series(SERIES_CODES["cpi_index"], start, end)
        rows.sort(key=lambda r: r[0])
        if len(rows) < 13:
            raise ProviderUnavailableError(self.code, "insufficient CPI history for YoY calc")
        latest_date, latest_value = rows[-1]
        year_ago_value = _find_value_months_ago(rows, months=12)
        if year_ago_value is None or year_ago_value == 0:
            raise ProviderUnavailableError(self.code, "no comparable CPI value 12 months back")
        yoy = (latest_value / year_ago_value - 1.0) * 100.0
        return [
            MacroObservationDTO(
                series_code=series_code,
                observation_date=latest_date,
                value=yoy,
                is_mock=False,
                fetched_at=now,
            )
        ]

    def _get_mock_series(self, series_code: str, now: dt.datetime) -> list[MacroObservationDTO]:
        return [
            MacroObservationDTO(
                series_code=series_code,
                observation_date=_MOCK_SEED_AS_OF,
                value=_MOCK_SEED[series_code],
                is_mock=True,
                fetched_at=now,
            )
        ]


def _find_value_months_ago(
    rows: list[tuple[dt.date, float]], months: int
) -> float | None:
    latest_date = rows[-1][0]
    target_year = latest_date.year - (months // 12)
    target_month = latest_date.month
    best: float | None = None
    for date, value in rows:
        if date.year == target_year and date.month == target_month:
            best = value
    return best
