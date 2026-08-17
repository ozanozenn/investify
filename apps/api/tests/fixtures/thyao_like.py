"""Deterministic fixture modeled on THYAO-shaped statements (roadmap
section 49: fixture-based testing for financial calculations). Numbers are
round, made-up figures chosen to make expected outputs easy to hand-verify
— NOT real THYAO data (see docs/DATA_FIXTURES note in README)."""

from __future__ import annotations

import datetime as dt

from app.schemas.financial import PeriodData


def annual_periods() -> list[PeriodData]:
    return [
        PeriodData(
            period_type="ANNUAL",
            fiscal_year=2022,
            period_end_date=dt.date(2022, 12, 31),
            values={
                "REVENUE": 1_000.0,
                "EBITDA": 200.0,
                "NET_INCOME": 80.0,
                "EQUITY": 500.0,
                "TOTAL_DEBT": 300.0,
                "CASH": 100.0,
                "TOTAL_ASSETS": 1_000.0,
                "OPERATING_CASH_FLOW": 150.0,
                "CAPEX": -50.0,
            },
        ),
        PeriodData(
            period_type="ANNUAL",
            fiscal_year=2023,
            period_end_date=dt.date(2023, 12, 31),
            values={
                "REVENUE": 1_100.0,
                "EBITDA": 220.0,
                "NET_INCOME": 90.0,
                "EQUITY": 560.0,
                "TOTAL_DEBT": 320.0,
                "CASH": 120.0,
                "TOTAL_ASSETS": 1_100.0,
                "OPERATING_CASH_FLOW": 170.0,
                "CAPEX": -55.0,
            },
        ),
        PeriodData(
            period_type="ANNUAL",
            fiscal_year=2024,
            period_end_date=dt.date(2024, 12, 31),
            values={
                "REVENUE": 1_210.0,
                "EBITDA": 250.0,
                "NET_INCOME": 100.0,
                "EQUITY": 620.0,
                "TOTAL_DEBT": 330.0,
                "CASH": 130.0,
                "TOTAL_ASSETS": 1_220.0,
                "OPERATING_CASH_FLOW": 190.0,
                "CAPEX": -60.0,
            },
        ),
        PeriodData(
            period_type="ANNUAL",
            fiscal_year=2025,
            period_end_date=dt.date(2025, 12, 31),
            values={
                "REVENUE": 1_331.0,
                "EBITDA": 280.0,
                "NET_INCOME": 115.0,
                "EQUITY": 690.0,
                "TOTAL_DEBT": 340.0,
                "CASH": 150.0,
                "TOTAL_ASSETS": 1_350.0,
                "OPERATING_CASH_FLOW": 210.0,
                "CAPEX": -65.0,
            },
        ),
    ]
