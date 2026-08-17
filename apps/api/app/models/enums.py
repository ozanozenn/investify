from __future__ import annotations

import enum


class PeriodType(str, enum.Enum):
    ANNUAL = "ANNUAL"
    QUARTERLY = "QUARTERLY"


class CanonicalField(str, enum.Enum):
    # Income statement
    REVENUE = "REVENUE"
    GROSS_PROFIT = "GROSS_PROFIT"
    EBITDA = "EBITDA"
    EBIT = "EBIT"
    NET_INCOME = "NET_INCOME"
    # Balance sheet
    CASH = "CASH"
    TOTAL_ASSETS = "TOTAL_ASSETS"
    TOTAL_DEBT = "TOTAL_DEBT"
    EQUITY = "EQUITY"
    # Cash flow
    OPERATING_CASH_FLOW = "OPERATING_CASH_FLOW"
    CAPEX = "CAPEX"
    FREE_CASH_FLOW = "FREE_CASH_FLOW"


class FetchStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


class DisclosureCategory(str, enum.Enum):
    FINANCIAL_RESULT = "FINANCIAL_RESULT"
    DIVIDEND = "DIVIDEND"
    INVESTMENT = "INVESTMENT"
    CONTRACT = "CONTRACT"
    MANAGEMENT = "MANAGEMENT"
    CAPITAL = "CAPITAL"
    OTHER = "OTHER"
