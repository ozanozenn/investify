from __future__ import annotations

import asyncio

import yfinance as yf

from app.providers.base import CompanyDataProvider, ProviderUnavailableError
from app.providers.company.seed import SEED_COMPANIES


class YFinanceCompanyDataProvider(CompanyDataProvider):
    """Resolves a ticker to a company profile: curated seed first (section
    90 validation companies), live yfinance profile as the general bootstrap
    path for any other BIST ticker (section 3.2)."""

    code = "yfinance"

    async def get_company_profile(self, ticker: str) -> dict:
        symbol = ticker.upper()
        if symbol in SEED_COMPANIES:
            seed = SEED_COMPANIES[symbol]
            return {**seed, "ticker": symbol, "source_code": "seed"}
        try:
            return await asyncio.to_thread(self._fetch_live, symbol)
        except Exception as exc:
            raise ProviderUnavailableError(self.code, f"company profile unavailable for {symbol}: {exc}") from exc

    def _fetch_live(self, symbol: str) -> dict:
        info = yf.Ticker(f"{symbol}.IS").info or {}
        name = info.get("longName") or info.get("shortName")
        if not name:
            raise ProviderUnavailableError(self.code, f"no profile for {symbol}")
        return {
            "ticker": symbol,
            "name": name,
            "sector": info.get("sector") or "Diğer",
            "industry": info.get("industry") or info.get("sector") or "Diğer",
            "is_financial_industry": (info.get("sector") or "").lower() in ("financial services", "financials"),
            "description": info.get("longBusinessSummary"),
            "website": info.get("website"),
            "kap_url": None,
            "employee_count": info.get("fullTimeEmployees"),
            "source_code": "yfinance",
        }
