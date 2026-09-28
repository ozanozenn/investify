from __future__ import annotations

import datetime as dt

import httpx
import pytest
import respx

from app.api.routers import calendar as calendar_router

_SAMPLE_DISCLOSURES = [
    {
        "publishDate": "28.09.2026 10:00:00",
        "kapTitle": "TÜRK HAVA YOLLARI A.Ş.",
        "summary": "Kar Payı Dağıtımına İlişkin Bildirim",
        "subject": "Kar Payı Dağıtım Tarihi",
        "disclosureIndex": 111,
        "stockCodes": "THYAO",
    },
    {
        "publishDate": "27.09.2026 09:30:00",
        "kapTitle": "ASELSAN A.Ş.",
        "summary": "Sermaye Artırımı Kararı",
        "subject": "Sermaye Artırımı",
        "disclosureIndex": 112,
        "stockCodes": "ASELS",
    },
    {
        "publishDate": "26.09.2026 09:30:00",
        "kapTitle": "YENİ ŞİRKET A.Ş.",
        "summary": "İzahname ve Halka Arz Tarihi Bilgileri",
        "subject": "İzahname ve Halka Arz Tarihi Bilgileri",
        "disclosureIndex": 113,
        "stockCodes": "YENIS",
    },
    {
        "publishDate": "25.09.2026 09:30:00",
        "kapTitle": "ARÇELİK A.Ş.",
        "summary": "Finansal Tablo Açıklaması",
        "subject": "Finansal Rapor",
        "disclosureIndex": 114,
        "stockCodes": "ARCLK",
    },
]


@pytest.mark.asyncio
async def test_rate_decisions_only_include_future_and_respect_limit(monkeypatch):
    today = dt.date.today()
    fake_config = {
        "meetings": [
            {"date": (today - dt.timedelta(days=5)).isoformat()},
            {"date": (today + dt.timedelta(days=3)).isoformat()},
            {"date": (today + dt.timedelta(days=10)).isoformat()},
            {"date": (today + dt.timedelta(days=20)).isoformat()},
        ]
    }
    monkeypatch.setattr(calendar_router, "get_tcmb_calendar_config", lambda: fake_config)

    with respx.mock:
        respx.route(host="www.kap.org.tr").mock(return_value=httpx.Response(200, json=[]))
        result = await calendar_router.get_calendar(upcoming_rate_decisions=2)

    assert [d.date.isoformat() for d in result.rate_decisions] == [
        (today + dt.timedelta(days=3)).isoformat(),
        (today + dt.timedelta(days=10)).isoformat(),
    ]


@pytest.mark.asyncio
async def test_company_events_filtered_to_dividend_capital_ipo_only(monkeypatch):
    monkeypatch.setattr(calendar_router, "get_tcmb_calendar_config", lambda: {"meetings": []})

    with respx.mock:
        respx.route(host="www.kap.org.tr").mock(return_value=httpx.Response(200, json=_SAMPLE_DISCLOSURES))
        result = await calendar_router.get_calendar()

    tickers = {e.ticker for e in result.company_events}
    assert tickers == {"THYAO", "ASELS", "YENIS"}
    assert "ARCLK" not in tickers  # FINANCIAL_RESULT is excluded from the events calendar

    categories = {e.ticker: e.category for e in result.company_events}
    assert categories["THYAO"] == "DIVIDEND"
    assert categories["ASELS"] == "CAPITAL"
    assert categories["YENIS"] == "IPO"


@pytest.mark.asyncio
async def test_company_events_sorted_most_recent_first(monkeypatch):
    monkeypatch.setattr(calendar_router, "get_tcmb_calendar_config", lambda: {"meetings": []})

    with respx.mock:
        respx.route(host="www.kap.org.tr").mock(return_value=httpx.Response(200, json=_SAMPLE_DISCLOSURES))
        result = await calendar_router.get_calendar()

    tickers_in_order = [e.ticker for e in result.company_events]
    assert tickers_in_order == ["THYAO", "ASELS", "YENIS"]
