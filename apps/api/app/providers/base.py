from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderUnavailableError(Exception):
    """Raised by a provider when it cannot fulfil a request.

    Callers (services/refresh_pipeline.py) MUST catch this per-stage and
    degrade gracefully (roadmap section 37) instead of letting it propagate.
    """

    def __init__(self, provider_code: str, message: str):
        self.provider_code = provider_code
        super().__init__(f"[{provider_code}] {message}")


@dataclass
class SourcedValue:
    """Wraps any externally-sourced value with traceability fields
    (roadmap section 22: source / source_url / fetched_at / published_at)."""

    value: object
    source_code: str
    fetched_at: dt.datetime
    source_url: str | None = None
    published_at: dt.datetime | None = None
    is_mock: bool = False


@dataclass
class Quote:
    ticker: str
    price: float
    currency: str
    market_cap: float | None
    shares_outstanding: float | None
    fifty_two_week_high: float | None
    fifty_two_week_low: float | None
    as_of: dt.datetime
    source_code: str
    fetched_at: dt.datetime
    # Sağlayıcı veriyorsa: önceki kapanış ve fiyatın borsadaki zamanı
    # (yfinance BIST için ~15 dk gecikmeli). Vermiyorsa None — tahmin edilmez.
    previous_close: float | None = None
    market_time: dt.datetime | None = None


@dataclass
class Candle:
    date: dt.date
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class RawFinancialPeriod:
    period_type: str  # "ANNUAL" | "QUARTERLY"
    fiscal_year: int
    fiscal_quarter: int | None
    period_end_date: dt.date
    currency: str
    values: dict[str, float]  # canonical field name -> value (base currency units)
    source_code: str
    fetched_at: dt.datetime


@dataclass
class RawDisclosure:
    kap_disclosure_index: int
    title: str
    subject: str | None
    published_at: dt.datetime
    source_url: str
    fetched_at: dt.datetime


@dataclass
class MacroObservationDTO:
    series_code: str
    observation_date: dt.date
    value: float
    is_mock: bool
    fetched_at: dt.datetime


@dataclass
class RawNewsItem:
    title: str
    source: str
    url: str
    published_at: dt.datetime
    fetched_at: dt.datetime


class MarketDataProvider(ABC):
    code: str

    @abstractmethod
    async def get_quote(self, ticker: str) -> Quote: ...

    @abstractmethod
    async def get_historical_prices(self, ticker: str, years: int = 5) -> list[Candle]: ...


class FinancialDataProvider(ABC):
    code: str

    @abstractmethod
    async def get_financial_statements(
        self, ticker: str, annual_years: int = 5, quarterly_quarters: int = 8
    ) -> list[RawFinancialPeriod]: ...


class DisclosureProvider(ABC):
    code: str

    @abstractmethod
    async def get_disclosures(
        self, ticker: str, lookback_days: int = 90, limit: int = 15
    ) -> list[RawDisclosure]: ...


class MacroDataProvider(ABC):
    code: str

    @abstractmethod
    async def get_series(self, series_code: str, lookback_days: int = 400) -> list[MacroObservationDTO]: ...


class CompanyDataProvider(ABC):
    """Static/bootstrap company reference data (name, sector, description)."""

    code: str

    @abstractmethod
    async def get_company_profile(self, ticker: str) -> dict: ...


class NewsProvider(ABC):
    """General market/company news — distinct from `DisclosureProvider`
    (KAP), which covers official regulatory disclosures only (Phase 4)."""

    code: str

    @abstractmethod
    async def get_news(self, ticker: str, company_name: str | None = None, limit: int = 15) -> list[RawNewsItem]: ...
