"""Maps yfinance's (Yahoo Finance) raw statement row labels to Investify's
canonical fields (ADR-004). Yahoo's row naming is not perfectly stable
across companies/versions, so each canonical field has an ordered list of
candidate labels — the first one present in the statement wins.
"""

from __future__ import annotations

from app.models.enums import CanonicalField

INCOME_STATEMENT_MAP: dict[CanonicalField, list[str]] = {
    CanonicalField.REVENUE: ["Total Revenue", "Operating Revenue"],
    CanonicalField.GROSS_PROFIT: ["Gross Profit"],
    CanonicalField.EBITDA: ["EBITDA", "Normalized EBITDA"],
    CanonicalField.EBIT: ["EBIT", "Operating Income"],
    CanonicalField.NET_INCOME: [
        "Net Income",
        "Net Income Common Stockholders",
        "Net Income From Continuing Operation Net Minority Interest",
    ],
}

BALANCE_SHEET_MAP: dict[CanonicalField, list[str]] = {
    CanonicalField.CASH: [
        "Cash And Cash Equivalents",
        "Cash Cash Equivalents And Short Term Investments",
    ],
    CanonicalField.TOTAL_ASSETS: ["Total Assets"],
    CanonicalField.TOTAL_DEBT: ["Total Debt"],
    CanonicalField.EQUITY: [
        "Stockholders Equity",
        "Common Stock Equity",
        "Total Equity Gross Minority Interest",
    ],
}

CASH_FLOW_MAP: dict[CanonicalField, list[str]] = {
    CanonicalField.OPERATING_CASH_FLOW: ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
    CanonicalField.CAPEX: ["Capital Expenditure", "Purchase Of PPE"],
    CanonicalField.FREE_CASH_FLOW: ["Free Cash Flow"],
}


def extract(row_map: dict[CanonicalField, list[str]], statement_index: list[str], column) -> dict[str, float]:
    """`column` is a pandas Series for one period (statement[period_column])."""
    result: dict[str, float] = {}
    for canonical, candidates in row_map.items():
        for label in candidates:
            if label in statement_index:
                value = column.get(label)
                if value is not None and value == value:  # not NaN
                    result[canonical.value] = float(value)
                    break
    return result
