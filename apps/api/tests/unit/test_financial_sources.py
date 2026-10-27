from __future__ import annotations

import datetime as dt

import pytest

from app.core.config import Settings
from app.providers.base import FinancialDataProvider, ProviderUnavailableError, RawFinancialPeriod
from app.providers.financial.composite_provider import (
    CompositeFinancialDataProvider,
    FinancialStatements,
    compare_periods,
    relative_difference,
)
from app.providers.financial.isyatirim_provider import IsYatirimFinancialDataProvider
from app.providers.financial.yfinance_provider import YFinanceFinancialDataProvider
from app.services.financial_sources import build_financial_provider, financial_source_warnings

_NOW = dt.datetime(2026, 10, 27, tzinfo=dt.timezone.utc)
_CFG = {
    "cross_check": {
        "relative_tolerance": 0.05,
        "period_types": ["ANNUAL"],
        "fields": ["REVENUE", "NET_INCOME", "EQUITY"],
        "max_warnings": 2,
    }
}


def _period(source: str, year: int, values: dict[str, float], period_type: str = "ANNUAL", quarter=None):
    return RawFinancialPeriod(
        period_type=period_type,
        fiscal_year=year,
        fiscal_quarter=quarter,
        period_end_date=dt.date(year, 12, 31),
        currency="TRY",
        values=values,
        source_code=source,
        fetched_at=_NOW,
    )


class StubProvider(FinancialDataProvider):
    def __init__(self, code: str, periods=None, error: Exception | None = None):
        self.code = code
        self._periods = periods or []
        self._error = error
        self.calls = 0

    async def get_financial_statements(self, ticker, annual_years=5, quarterly_quarters=8):
        self.calls += 1
        if self._error:
            raise self._error
        return list(self._periods)


def _composite(primary, fallback, cross_check=False):
    return CompositeFinancialDataProvider(
        primary,
        fallback,
        cross_check=cross_check,
        tolerance=0.05,
        cross_check_fields=["REVENUE", "NET_INCOME", "EQUITY"],
        cross_check_period_types=["ANNUAL"],
    )


# --- relative difference / comparison ---------------------------------------


def test_relative_difference_is_symmetric_and_safe_at_zero():
    assert relative_difference(100.0, 90.0) == pytest.approx(0.1)
    assert relative_difference(90.0, 100.0) == pytest.approx(0.1)
    assert relative_difference(0.0, 0.0) == 0.0
    assert relative_difference(-10.0, 10.0) == pytest.approx(2.0)


def test_compare_periods_flags_only_shared_fields_beyond_tolerance():
    primary = [
        _period("isyatirim", 2025, {"REVENUE": 1000.0, "NET_INCOME": 100.0, "EQUITY": 500.0}),
        _period("isyatirim", 2024, {"REVENUE": 900.0, "NET_INCOME": 80.0}),
        _period("isyatirim", 2023, {"REVENUE": 800.0}),  # no counterpart period
        _period("isyatirim", 2025, {"REVENUE": 1.0}, period_type="QUARTERLY", quarter=4),
    ]
    secondary = [
        _period("yfinance", 2025, {"REVENUE": 1030.0, "NET_INCOME": 120.0}),  # 2.9% ok, 16.7% flagged
        _period("yfinance", 2024, {"REVENUE": 1000.0, "NET_INCOME": 80.0, "EQUITY": 1.0}),
        _period("yfinance", 2025, {"REVENUE": 99.0}, period_type="QUARTERLY", quarter=4),
    ]

    found = compare_periods(primary, secondary, ["REVENUE", "NET_INCOME", "EQUITY"], ["ANNUAL"], 0.05)

    assert [(d.fiscal_year, d.field) for d in found] == [(2025, "NET_INCOME"), (2024, "REVENUE")]
    first = found[0]
    assert (first.primary_source, first.primary_value) == ("isyatirim", 100.0)
    assert (first.secondary_source, first.secondary_value) == ("yfinance", 120.0)
    assert first.relative_difference == pytest.approx(20 / 120)


# --- composite provider -----------------------------------------------------


@pytest.mark.asyncio
async def test_primary_success_skips_fallback_without_cross_check():
    primary = StubProvider("isyatirim", [_period("isyatirim", 2025, {"REVENUE": 1.0})])
    fallback = StubProvider("yfinance", [_period("yfinance", 2025, {"REVENUE": 2.0})])

    result = await _composite(primary, fallback).get_financial_statements("THYAO")

    assert isinstance(result, FinancialStatements)
    assert [p.source_code for p in result] == ["isyatirim"]
    assert fallback.calls == 0
    assert result.used_source == "isyatirim"
    assert not result.fallback_used
    assert result.discrepancies == []
    assert financial_source_warnings(result, max_warnings=2) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "primary",
    [
        StubProvider("isyatirim", error=ProviderUnavailableError("isyatirim", "down")),
        StubProvider("isyatirim", periods=[]),  # "returns nothing"
        StubProvider("isyatirim", error=RuntimeError("parser bug")),
    ],
)
async def test_fallback_used_when_primary_fails_or_is_empty(primary):
    fallback = StubProvider("yfinance", [_period("yfinance", 2025, {"REVENUE": 2.0})])

    result = await _composite(primary, fallback).get_financial_statements("THYAO")

    assert [p.source_code for p in result] == ["yfinance"]
    assert result.fallback_used
    assert result.used_source == "yfinance"
    assert financial_source_warnings(result, max_warnings=2) == [
        "Birincil finansal tablo kaynağı (İş Yatırım) veri vermedi; yedek kaynak (Yahoo Finance) kullanıldı."
    ]


@pytest.mark.asyncio
async def test_both_sources_failing_raises_provider_unavailable():
    primary = StubProvider("isyatirim", error=ProviderUnavailableError("isyatirim", "down"))
    fallback = StubProvider("yfinance", error=ProviderUnavailableError("yfinance", "also down"))

    with pytest.raises(ProviderUnavailableError, match="also down"):
        await _composite(primary, fallback, cross_check=True).get_financial_statements("THYAO")
    assert fallback.calls == 1  # not re-queried after the concurrent cross-check call


@pytest.mark.asyncio
async def test_cross_check_records_discrepancies_but_keeps_primary_values():
    primary = StubProvider(
        "isyatirim",
        [
            _period("isyatirim", 2025, {"REVENUE": 1000.0, "NET_INCOME": 100.0, "EQUITY": 500.0}),
            _period("isyatirim", 2024, {"REVENUE": 900.0, "NET_INCOME": 90.0}),
            _period("isyatirim", 2023, {"REVENUE": 800.0}),
            _period("isyatirim", 2022, {"REVENUE": 700.0}),
        ],
    )
    fallback = StubProvider(
        "yfinance",
        [
            _period("yfinance", 2025, {"REVENUE": 1200.0, "NET_INCOME": 100.0, "EQUITY": 400.0}),
            _period("yfinance", 2024, {"REVENUE": 900.0, "NET_INCOME": 50.0}),
            _period("yfinance", 2023, {"REVENUE": 1.0}),
            _period("yfinance", 2022, {"REVENUE": 1.0}),
        ],
    )

    result = await _composite(primary, fallback, cross_check=True).get_financial_statements("THYAO")

    assert result[0].values["REVENUE"] == 1000.0  # primary value used, never silently swapped
    assert {(d.fiscal_year, d.field) for d in result.discrepancies} == {
        (2025, "REVENUE"), (2025, "EQUITY"), (2024, "NET_INCOME"), (2023, "REVENUE"), (2022, "REVENUE"),
    }
    warnings = financial_source_warnings(result, max_warnings=2)
    assert warnings == [
        "Finansal tablo çapraz kontrolü (2025 yıllık): Hasılat, Özkaynaklar için İş Yatırım ile "
        "Yahoo Finance değerleri tolerans dışında farklı; İş Yatırım değerleri kullanıldı.",
        "Finansal tablo çapraz kontrolü (2024 yıllık): Net kâr için İş Yatırım ile "
        "Yahoo Finance değerleri tolerans dışında farklı; İş Yatırım değerleri kullanıldı.",
        "Finansal tablo çapraz kontrolü: 2 dönemde daha kaynaklar arası fark var.",
    ]


@pytest.mark.asyncio
async def test_cross_check_with_failing_secondary_still_returns_primary():
    primary = StubProvider("yfinance", [_period("yfinance", 2025, {"REVENUE": 1.0})])
    fallback = StubProvider("isyatirim", error=ProviderUnavailableError("isyatirim", "blocked"))

    result = await _composite(primary, fallback, cross_check=True).get_financial_statements("THYAO")

    assert [p.source_code for p in result] == ["yfinance"]
    assert result.cross_check_skipped
    assert financial_source_warnings(result, max_warnings=2) == [
        "Finansal tablo çapraz kontrolü yapılamadı: İş Yatırım veri vermedi."
    ]


def test_plain_list_produces_no_warnings():
    assert financial_source_warnings([_period("yfinance", 2025, {})], max_warnings=2) == []
    assert financial_source_warnings([], max_warnings=2) == []


def test_warnings_default_cap_comes_from_yaml_config():
    result = FinancialStatements(primary_source="isyatirim", secondary_source="yfinance")
    assert financial_source_warnings(result) == []  # loads config/financial_sources.yaml


# --- settings -> provider ---------------------------------------------------


def _settings(**overrides) -> Settings:
    # Never read a developer's local .env in unit tests.
    return Settings(_env_file=None, **overrides)


def test_defaults_are_yfinance_only():
    fields = Settings.model_fields
    assert fields["financial_provider_primary"].default == "yfinance"
    assert fields["financial_provider_fallback"].default == "none"
    assert fields["financial_cross_check"].default is False


def test_default_settings_keep_plain_yfinance_provider():
    settings = _settings(
        financial_provider_primary="yfinance", financial_provider_fallback="none", financial_cross_check=False
    )
    provider = build_financial_provider(settings, cross_check_config=_CFG)
    assert type(provider) is YFinanceFinancialDataProvider
    assert provider.code == "yfinance"


def test_cross_check_without_fallback_is_ignored():
    settings = _settings(
        financial_provider_primary="yfinance", financial_provider_fallback="none", financial_cross_check=True
    )
    assert type(build_financial_provider(settings, cross_check_config=_CFG)) is YFinanceFinancialDataProvider


def test_isyatirim_primary_with_yfinance_fallback_and_cross_check():
    settings = _settings(
        financial_provider_primary="isyatirim",
        financial_provider_fallback="yfinance",
        financial_cross_check=True,
    )
    provider = build_financial_provider(settings, cross_check_config=_CFG)
    assert isinstance(provider, CompositeFinancialDataProvider)
    assert isinstance(provider.primary, IsYatirimFinancialDataProvider)
    assert isinstance(provider.fallback, YFinanceFinancialDataProvider)
    assert provider.code == "isyatirim+yfinance"
    assert provider.cross_check is True
    assert provider.tolerance == 0.05
    assert provider.cross_check_fields == ["REVENUE", "NET_INCOME", "EQUITY"]


def test_same_primary_and_fallback_collapses_to_single_provider():
    settings = _settings(financial_provider_primary="isyatirim", financial_provider_fallback="isyatirim")
    assert type(build_financial_provider(settings, cross_check_config=_CFG)) is IsYatirimFinancialDataProvider


def test_invalid_provider_name_is_rejected_by_settings():
    with pytest.raises(ValueError):
        _settings(financial_provider_primary="kap")
