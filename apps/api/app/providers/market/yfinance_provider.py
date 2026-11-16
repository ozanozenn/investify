from __future__ import annotations

import asyncio
import datetime as dt

import yfinance as yf

from app.core.logging import get_logger
from app.providers.base import Candle, MarketDataProvider, ProviderUnavailableError, Quote

logger = get_logger(__name__)


def _yahoo_symbol(ticker: str, exchange: str = "BIST") -> str:
    return f"{ticker.upper()}.IS" if exchange == "BIST" else ticker.upper()


def _market_time(raw: object) -> dt.datetime | None:
    """`regularMarketTime` (epoch saniye) -> UTC datetime; tanınmazsa None."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or raw <= 0:
        return None
    return dt.datetime.fromtimestamp(raw, tz=dt.timezone.utc)


class YFinanceMarketDataProvider(MarketDataProvider):
    code = "yfinance"

    async def get_quote(self, ticker: str) -> Quote:
        try:
            return await asyncio.to_thread(self._get_quote_sync, ticker)
        except ProviderUnavailableError:
            raise
        except Exception as exc:  # yfinance raises assorted network/parsing errors
            raise ProviderUnavailableError(self.code, f"get_quote({ticker}) failed: {exc}") from exc

    def _get_quote_sync(self, ticker: str) -> Quote:
        yt = yf.Ticker(_yahoo_symbol(ticker))
        info = yt.info or {}
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price is None:
            raise ProviderUnavailableError(self.code, f"no price data for {ticker}")
        now = dt.datetime.now(dt.timezone.utc)
        previous_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
        return Quote(
            ticker=ticker.upper(),
            price=float(price),
            currency=info.get("currency", "TRY"),
            market_cap=info.get("marketCap"),
            shares_outstanding=info.get("sharesOutstanding"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
            as_of=now,
            source_code=self.code,
            fetched_at=now,
            previous_close=float(previous_close) if previous_close else None,
            market_time=_market_time(info.get("regularMarketTime")),
        )

    async def get_historical_prices(self, ticker: str, years: int = 5) -> list[Candle]:
        try:
            return await asyncio.to_thread(self._get_history_sync, ticker, years)
        except ProviderUnavailableError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError(
                self.code, f"get_historical_prices({ticker}) failed: {exc}"
            ) from exc

    def _get_history_sync(self, ticker: str, years: int) -> list[Candle]:
        yt = yf.Ticker(_yahoo_symbol(ticker))
        hist = yt.history(period=f"{years}y")
        if hist is None or hist.empty:
            raise ProviderUnavailableError(self.code, f"no historical data for {ticker}")
        candles: list[Candle] = []
        for idx, row in hist.iterrows():
            candles.append(
                Candle(
                    date=idx.date(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]),
                )
            )
        return candles


class YFinanceFxProvider:
    """Free FX quotes (USD/TRY, EUR/TRY) — no key required (ADR-002)."""

    code = "yfinance_fx"

    async def get_rate(self, pair: str) -> float | None:
        try:
            return await asyncio.to_thread(self._get_rate_sync, pair)
        except Exception as exc:
            logger.warning("fx_fetch_failed", extra={"pair": pair, "error": str(exc)})
            return None

    def _get_rate_sync(self, pair: str) -> float | None:
        yt = yf.Ticker(f"{pair}=X")
        info = yt.info or {}
        price = info.get("regularMarketPrice") or info.get("previousClose")
        return float(price) if price is not None else None
