"""Smoke test for scripts/verify_isyatirim.py — the owner runs it against the
live APIs; here it runs against stub providers so it cannot silently rot."""

from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path

import pytest

from app.providers.base import FinancialDataProvider, ProviderUnavailableError, RawFinancialPeriod

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_isyatirim.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("verify_isyatirim", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Stub(FinancialDataProvider):
    def __init__(self, code: str, revenue: float | None):
        self.code = code
        self.revenue = revenue

    async def get_financial_statements(self, ticker, annual_years=5, quarterly_quarters=8):
        if self.revenue is None:
            raise ProviderUnavailableError(self.code, "down")
        return [
            RawFinancialPeriod(
                period_type="ANNUAL",
                fiscal_year=2025,
                fiscal_quarter=None,
                period_end_date=dt.date(2025, 12, 31),
                currency="TRY",
                values={"REVENUE": self.revenue, "NET_INCOME": 10.0},
                source_code=self.code,
                fetched_at=dt.datetime.now(dt.timezone.utc),
            )
        ]


async def _run(script, isy, yf):
    lines: list[str] = []
    code = await script.run(
        ["thyao"],
        isy,
        yf,
        annual_years=5,
        quarters=8,
        include_quarterly=False,
        show_codes=False,
        tolerance=0.05,
        fields=["REVENUE", "NET_INCOME"],
        out=lines.append,
    )
    return code, "\n".join(lines)


@pytest.mark.asyncio
async def test_script_prints_side_by_side_and_cross_check():
    script = _load_script()
    code, output = await _run(script, _Stub("isyatirim", 1_000_000_000.0), _Stub("yfinance", 1_200_000_000.0))
    assert code == 0
    assert "=== THYAO ===" in output
    assert "2025 yıllık" in output
    assert "Hasılat" in output
    assert "1 fark" in output
    assert "FINANCIAL_PROVIDER_PRIMARY=isyatirim" in output


@pytest.mark.asyncio
async def test_script_fails_when_isyatirim_returns_nothing():
    script = _load_script()
    code, output = await _run(script, _Stub("isyatirim", None), _Stub("yfinance", 1.0))
    assert code == 1
    assert "HATA" in output
    assert "DEĞİŞTİRMEYİN" in output
