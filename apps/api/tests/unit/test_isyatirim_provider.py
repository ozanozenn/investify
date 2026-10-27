from __future__ import annotations

import datetime as dt

import httpx
import pytest
import respx

from app.providers.base import ProviderUnavailableError
from app.providers.financial.isyatirim_mapping import (
    ResolvedValue,
    discrete_quarter_values,
    parse_item_value,
    resolve_period,
)
from app.providers.financial.isyatirim_provider import (
    MALI_TABLO_PATH,
    IsYatirimFinancialDataProvider,
    extract_rows,
    parse_year_rows,
)
from tests.fixtures.isyatirim_malitablo import (
    M,
    cumulative_year,
    empty_payload,
    partial_year,
    year_payload,
)

_TODAY = dt.date(2026, 10, 27)
_HOST = "www.isyatirim.com.tr"


def _provider() -> IsYatirimFinancialDataProvider:
    return IsYatirimFinancialDataProvider(request_interval_seconds=0, today=lambda: _TODAY)


def _mock_years(payloads_by_year: dict[int, dict]) -> list[dict]:
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        calls.append(params)
        return httpx.Response(200, json=payloads_by_year.get(int(params["year1"]), empty_payload()))

    respx.route(host=_HOST, path=MALI_TABLO_PATH).mock(side_effect=handler)
    return calls


def _standard_history() -> dict[int, dict]:
    return {
        2026: year_payload(partial_year(cumulative_year(1.3), reported_periods=2)),
        2025: year_payload(cumulative_year(1.2)),
        2024: year_payload(cumulative_year(1.1)),
        2023: year_payload(cumulative_year(1.0)),
        2022: year_payload(cumulative_year(0.9)),
        2021: year_payload(cumulative_year(0.8)),
    }


# --- parsing helpers ---------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2360037000000", 2360037000000.0),
        ("-43613000000", -43613000000.0),
        (" 1125149219659 ", 1125149219659.0),
        (12.5, 12.5),
        ("0", 0.0),
        (None, None),
        ("", None),
        ("null", None),
        ("1,5", None),  # ambiguous Turkish decimal comma: never guessed
        ("abc", None),
        ("NaN", None),
        (True, None),
    ],
)
def test_parse_item_value(raw, expected):
    assert parse_item_value(raw) == expected


def test_extract_rows_rejects_error_envelope_and_missing_value():
    with pytest.raises(ProviderUnavailableError):
        extract_rows({"ok": False, "errorDescription": "Geçersiz istek", "value": None})
    with pytest.raises(ProviderUnavailableError):
        extract_rows({"ok": True})
    with pytest.raises(ProviderUnavailableError):
        extract_rows("<html>blocked</html>")
    assert extract_rows(empty_payload()) == []


def test_parse_year_rows_drops_unpublished_and_zero_asset_periods():
    values = partial_year(cumulative_year(), reported_periods=2)
    values["1BL"][1] = 0.0  # period 6 has a zero total-assets row -> not a reported period
    parsed = parse_year_rows(year_payload(values)["value"], 2026)
    assert list(parsed) == [(2026, 3)]
    assert parsed[(2026, 3)]["3C"] == 100 * M


def test_resolve_period_maps_codes_and_sums():
    items = {"3C": 10.0, "3Z": 2.0, "3L": 3.0, "2O": 40.0, "2N": 50.0, "2AA": 5.0, "2BA": 7.0, "3H": 4.0, "4B": 1.0}
    resolved = resolve_period(items)
    assert resolved["REVENUE"].value == 10.0
    assert resolved["NET_INCOME"] == ResolvedValue(2.0, "3Z")  # parent share preferred over 3L
    assert resolved["EQUITY"] == ResolvedValue(40.0, "2O")  # parent equity preferred over 2N
    assert resolved["TOTAL_DEBT"] == ResolvedValue(12.0, "2AA+2BA")
    assert resolved["EBITDA"] == ResolvedValue(5.0, "3H+4B")
    assert "FREE_CASH_FLOW" not in resolved  # 4CB is a different FCF definition, not mapped


def test_resolve_period_fallbacks_and_missing_components():
    resolved = resolve_period({"3L": 3.0, "2N": 50.0, "2AA": 5.0, "3H": 4.0})
    assert resolved["NET_INCOME"] == ResolvedValue(3.0, "3L")
    assert resolved["EQUITY"] == ResolvedValue(50.0, "2N")
    # A sum is never built from a partial set of its components.
    assert "TOTAL_DEBT" not in resolved
    assert "EBITDA" not in resolved


def test_discrete_quarter_requires_previous_cumulative_from_same_code():
    current = {"REVENUE": ResolvedValue(220.0, "3C"), "TOTAL_ASSETS": ResolvedValue(9.0, "1BL"),
               "NET_INCOME": ResolvedValue(25.0, "3Z")}
    previous = {"REVENUE": ResolvedValue(100.0, "3C"), "NET_INCOME": ResolvedValue(11.0, "3L")}
    values = discrete_quarter_values(current, previous, fiscal_quarter=2)
    assert values["REVENUE"] == 120.0
    assert values["TOTAL_ASSETS"] == 9.0  # balance sheet: snapshot, not differenced
    assert "NET_INCOME" not in values  # 3Z vs 3L: not comparable, left out
    # No previous period at all: only balance-sheet fields survive.
    assert discrete_quarter_values(current, None, fiscal_quarter=2) == {"TOTAL_ASSETS": 9.0}
    # Q1 is already a single quarter.
    assert discrete_quarter_values(current, None, fiscal_quarter=1)["REVENUE"] == 220.0


# --- provider end to end (HTTP mocked) --------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_annual_periods_are_mapped_from_full_year_values():
    _mock_years(_standard_history())

    periods = await _provider().get_financial_statements("thyao", annual_years=5, quarterly_quarters=8)

    annual = [p for p in periods if p.period_type == "ANNUAL"]
    assert [p.fiscal_year for p in annual] == [2025, 2024, 2023, 2022, 2021]
    fy25 = annual[0]
    assert fy25.source_code == "isyatirim"
    assert fy25.currency == "TRY"
    assert fy25.period_end_date == dt.date(2025, 12, 31)
    assert fy25.fiscal_quarter is None
    v = fy25.values
    assert v["REVENUE"] == pytest.approx(500 * 1.2 * M)
    assert v["GROSS_PROFIT"] == pytest.approx(150 * 1.2 * M)
    assert v["EBIT"] == pytest.approx(94 * 1.2 * M)
    assert v["EBITDA"] == pytest.approx((90 + 20) * 1.2 * M)
    assert v["NET_INCOME"] == pytest.approx(70 * 1.2 * M)
    assert v["EQUITY"] == pytest.approx(510 * 1.2 * M)
    assert v["TOTAL_DEBT"] == pytest.approx((65 + 180) * 1.2 * M)
    assert v["CASH"] == pytest.approx(95 * 1.2 * M)
    assert v["TOTAL_ASSETS"] == pytest.approx(1300 * 1.2 * M)
    assert v["OPERATING_CASH_FLOW"] == pytest.approx(130 * 1.2 * M)
    assert v["CAPEX"] == pytest.approx(-52 * 1.2 * M)
    assert "FREE_CASH_FLOW" not in v


@pytest.mark.asyncio
@respx.mock
async def test_quarterly_periods_are_single_quarter_values():
    _mock_years(_standard_history())

    periods = await _provider().get_financial_statements("THYAO", annual_years=5, quarterly_quarters=8)

    quarterly = [p for p in periods if p.period_type == "QUARTERLY"]
    assert [(p.fiscal_year, p.fiscal_quarter) for p in quarterly] == [
        (2026, 2), (2026, 1), (2025, 4), (2025, 3), (2025, 2), (2025, 1), (2024, 4), (2024, 3),
    ]
    q2_2026, q1_2026, q4_2025 = quarterly[0], quarterly[1], quarterly[2]
    assert q2_2026.period_end_date == dt.date(2026, 6, 30)
    assert q2_2026.values["REVENUE"] == pytest.approx(120 * 1.3 * M)  # H1 - Q1
    assert q1_2026.values["REVENUE"] == pytest.approx(100 * 1.3 * M)  # Q1 as reported
    assert q4_2025.values["REVENUE"] == pytest.approx(150 * 1.2 * M)  # FY - 9M
    assert q4_2025.values["EBITDA"] == pytest.approx((24 + 5) * 1.2 * M)
    assert q4_2025.values["CAPEX"] == pytest.approx(-16 * 1.2 * M)
    # Balance-sheet items are period-end snapshots, never differenced.
    assert q2_2026.values["TOTAL_ASSETS"] == pytest.approx(1100 * 1.3 * M)
    assert q2_2026.values["TOTAL_DEBT"] == pytest.approx((55 + 160) * 1.3 * M)


@pytest.mark.asyncio
@respx.mock
async def test_request_uses_four_period_pairs_per_year_for_xi29():
    calls = _mock_years(_standard_history())

    await _provider().get_financial_statements("THYAO", annual_years=5, quarterly_quarters=8)

    assert [int(c["year1"]) for c in calls] == [2026, 2025, 2024, 2023, 2022, 2021]
    first = calls[0]
    assert first["companyCode"] == "THYAO"
    assert first["exchange"] == "TRY"
    assert first["financialGroup"] == "XI_29"
    assert [first[f"period{i}"] for i in range(1, 5)] == ["3", "6", "9", "12"]
    assert {first[f"year{i}"] for i in range(1, 5)} == {"2026"}


@pytest.mark.asyncio
@respx.mock
async def test_history_stops_at_first_empty_past_year():
    history = _standard_history()
    del history[2023], history[2022], history[2021]  # e.g. listed in 2024
    calls = _mock_years(history)

    periods = await _provider().get_financial_statements("NEWCO", annual_years=5, quarterly_quarters=8)

    assert [int(c["year1"]) for c in calls] == [2026, 2025, 2024, 2023]
    assert [p.fiscal_year for p in periods if p.period_type == "ANNUAL"] == [2025, 2024]


@pytest.mark.asyncio
@respx.mock
async def test_non_xi29_company_raises_after_two_empty_years():
    calls = _mock_years({})  # banks etc.: XI_29 returns an empty value list

    with pytest.raises(ProviderUnavailableError, match="no XI_29 statements"):
        await _provider().get_financial_statements("GARAN")
    assert len(calls) == 2


@pytest.mark.asyncio
@respx.mock
async def test_http_error_becomes_provider_unavailable():
    respx.route(host=_HOST, path=MALI_TABLO_PATH).mock(return_value=httpx.Response(503))
    with pytest.raises(ProviderUnavailableError):
        await _provider().get_financial_statements("THYAO")


@pytest.mark.asyncio
@respx.mock
async def test_html_soft_block_becomes_provider_unavailable():
    respx.route(host=_HOST, path=MALI_TABLO_PATH).mock(
        return_value=httpx.Response(200, text="<html>Request blocked</html>")
    )
    with pytest.raises(ProviderUnavailableError, match="non-JSON"):
        await _provider().get_financial_statements("THYAO")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_raw_rows_returns_labels_for_verification():
    _mock_years(_standard_history())
    rows = await _provider().fetch_raw_rows("thyao", 2025)
    labels = {r["itemCode"]: r["itemDescTr"].strip() for r in rows}
    assert labels["3C"] == "Satış Gelirleri"
    assert labels["1BL"] == "TOPLAM VARLIKLAR"
