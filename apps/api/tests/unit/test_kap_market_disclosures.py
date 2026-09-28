from __future__ import annotations

import httpx
import pytest
import respx

from app.models.enums import DisclosureCategory
from app.providers.base import ProviderUnavailableError
from app.providers.disclosure.kap_provider import KapDisclosureProvider

_SAMPLE_RESPONSE = [
    {
        "publishDate": "28.09.2026 10:00:00",
        "kapTitle": "TÜRK HAVA YOLLARI A.Ş.",
        "summary": "Kar Payı Dağıtımına İlişkin Bildirim",
        "subject": "Kar Payı Dağıtım Tarihi",
        "disclosureIndex": 111,
        "stockCodes": "THYAO",
    },
    {
        "publishDate": "28.09.2026 09:30:00",
        "kapTitle": "ASELSAN A.Ş.",
        "summary": "Sermaye Artırımı Kararı",
        "subject": "Sermaye Artırımı",
        "disclosureIndex": 112,
        "stockCodes": "ASELS",
    },
    {
        "publishDate": "27.09.2026 18:00:00",
        "kapTitle": "BORSA İSTANBUL A.Ş.",
        "summary": "Test bildirimi",
        "subject": "Genel Bilgi",
        "disclosureIndex": 113,
        "stockCodes": None,
    },
    {
        # Real-world case (found via live verification 2026-09-28): `subject`
        # is a generic regulatory template name, the real signal is only in
        # `summary` — categorize() must consider both, not just `subject`.
        "publishDate": "27.09.2026 12:00:00",
        "kapTitle": "PCILT A.Ş.",
        "summary": "25.09.2026 Tarihli Pay Geri Alım İşlemleri",
        "subject": "Özel Durum Açıklaması (Genel)",
        "disclosureIndex": 115,
        "stockCodes": "PCILT",
    },
]


@pytest.mark.asyncio
@respx.mock
async def test_market_disclosures_are_market_wide_not_ticker_scoped():
    route = respx.route(host="www.kap.org.tr").mock(return_value=httpx.Response(200, json=_SAMPLE_RESPONSE))
    provider = KapDisclosureProvider()

    items = await provider.get_market_disclosures(limit=30)

    assert len(items) == 4
    body = route.calls.last.request.content
    assert b'"mkkMemberOidList":[]' in body


@pytest.mark.asyncio
@respx.mock
async def test_market_disclosures_are_categorized_and_ticker_extracted():
    respx.route(host="www.kap.org.tr").mock(return_value=httpx.Response(200, json=_SAMPLE_RESPONSE))
    provider = KapDisclosureProvider()

    items = await provider.get_market_disclosures(limit=30)

    dividend = next(i for i in items if i.ticker == "THYAO")
    assert dividend.category == DisclosureCategory.DIVIDEND
    capital = next(i for i in items if i.ticker == "ASELS")
    assert capital.category == DisclosureCategory.CAPITAL
    no_ticker = next(i for i in items if i.company_name == "BORSA İSTANBUL A.Ş.")
    assert no_ticker.ticker is None


@pytest.mark.asyncio
@respx.mock
async def test_category_signal_in_summary_is_used_when_subject_is_generic():
    respx.route(host="www.kap.org.tr").mock(return_value=httpx.Response(200, json=_SAMPLE_RESPONSE))
    provider = KapDisclosureProvider()

    items = await provider.get_market_disclosures(limit=30)

    buyback = next(i for i in items if i.ticker == "PCILT")
    assert buyback.category == DisclosureCategory.CAPITAL


@pytest.mark.asyncio
@respx.mock
async def test_market_disclosures_respects_limit():
    respx.route(host="www.kap.org.tr").mock(return_value=httpx.Response(200, json=_SAMPLE_RESPONSE))
    provider = KapDisclosureProvider()

    items = await provider.get_market_disclosures(limit=1)
    assert len(items) == 1


@pytest.mark.asyncio
@respx.mock
async def test_market_disclosures_http_error_raises_provider_unavailable():
    respx.route(host="www.kap.org.tr").mock(side_effect=httpx.ConnectError("network down"))
    provider = KapDisclosureProvider()

    with pytest.raises(ProviderUnavailableError):
        await provider.get_market_disclosures()
