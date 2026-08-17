from __future__ import annotations

import asyncio
import datetime as dt

import yfinance as yf

from app.providers.base import FinancialDataProvider, ProviderUnavailableError, RawFinancialPeriod
from app.providers.financial.yfinance_mapping import (
    BALANCE_SHEET_MAP,
    CASH_FLOW_MAP,
    INCOME_STATEMENT_MAP,
    extract,
)


def _yahoo_symbol(ticker: str) -> str:
    return f"{ticker.upper()}.IS"


class YFinanceFinancialDataProvider(FinancialDataProvider):
    code = "yfinance"

    async def get_financial_statements(
        self, ticker: str, annual_years: int = 5, quarterly_quarters: int = 8
    ) -> list[RawFinancialPeriod]:
        try:
            return await asyncio.to_thread(
                self._get_statements_sync, ticker, annual_years, quarterly_quarters
            )
        except ProviderUnavailableError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError(
                self.code, f"get_financial_statements({ticker}) failed: {exc}"
            ) from exc

    def _get_statements_sync(
        self, ticker: str, annual_years: int, quarterly_quarters: int
    ) -> list[RawFinancialPeriod]:
        yt = yf.Ticker(_yahoo_symbol(ticker))
        periods: list[RawFinancialPeriod] = []
        periods += self._build_periods(
            yt.financials, yt.balance_sheet, yt.cashflow, "ANNUAL", annual_years, ticker
        )
        periods += self._build_periods(
            yt.quarterly_financials,
            yt.quarterly_balance_sheet,
            yt.quarterly_cashflow,
            "QUARTERLY",
            quarterly_quarters,
            ticker,
        )
        if not periods:
            raise ProviderUnavailableError(self.code, f"no financial statements for {ticker}")
        return periods

    def _build_periods(
        self, income, balance, cashflow, period_type: str, limit: int, ticker: str
    ) -> list[RawFinancialPeriod]:
        if income is None or income.empty:
            return []
        now = dt.datetime.now(dt.timezone.utc)
        out: list[RawFinancialPeriod] = []
        for col in list(income.columns)[:limit]:
            period_end: dt.date = col.date() if hasattr(col, "date") else col
            values: dict[str, float] = {}
            values.update(extract(INCOME_STATEMENT_MAP, income.index, income[col]))
            if balance is not None and not balance.empty and col in balance.columns:
                values.update(extract(BALANCE_SHEET_MAP, balance.index, balance[col]))
            if cashflow is not None and not cashflow.empty and col in cashflow.columns:
                values.update(extract(CASH_FLOW_MAP, cashflow.index, cashflow[col]))
            if not values:
                continue
            fiscal_quarter = None
            if period_type == "QUARTERLY":
                fiscal_quarter = (period_end.month - 1) // 3 + 1
            out.append(
                RawFinancialPeriod(
                    period_type=period_type,
                    fiscal_year=period_end.year,
                    fiscal_quarter=fiscal_quarter,
                    period_end_date=period_end,
                    currency="TRY",
                    values=values,
                    source_code=self.code,
                    fetched_at=now,
                )
            )
        return out
