from __future__ import annotations

import httpx
import pytest
import respx

from app.providers.base import ProviderUnavailableError
from app.providers.news.google_news_provider import GoogleNewsProvider

_SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item>
  <title>THYAO hisseleri günü yükselişle kapattı - Mynet Finans</title>
  <link>https://news.google.com/rss/articles/AAA</link>
  <pubDate>Wed, 16 Sep 2026 16:14:00 GMT</pubDate>
  <source url="https://finans.mynet.com">Mynet Finans</source>
</item>
<item>
  <title>THYAO hisseleri günü yükselişle kapattı - Bloomberg HT</title>
  <link>https://news.google.com/rss/articles/BBB</link>
  <pubDate>Wed, 16 Sep 2026 16:10:00 GMT</pubDate>
  <source url="https://bloomberght.com">Bloomberg HT</source>
</item>
<item>
  <title>THY filosuna yeni uçak katıldı - Anadolu Ajansı</title>
  <link>https://news.google.com/rss/articles/CCC</link>
  <pubDate>Tue, 15 Sep 2026 09:00:00 GMT</pubDate>
  <source url="https://aa.com.tr">Anadolu Ajansı</source>
</item>
<item>
  <title>Kaynaksız haber başlığı</title>
  <link>https://news.google.com/rss/articles/DDD</link>
  <pubDate>Mon, 14 Sep 2026 08:00:00 GMT</pubDate>
</item>
</channel></rss>"""


@pytest.mark.asyncio
@respx.mock
async def test_near_duplicate_titles_are_deduplicated():
    respx.route(host="news.google.com").mock(return_value=httpx.Response(200, text=_SAMPLE_RSS))
    provider = GoogleNewsProvider()

    items = await provider.get_news("THYAO", limit=15)

    # 4 raw items, but items 1 and 2 are near-duplicates (same headline,
    # different outlet) -> only one should survive.
    assert len(items) == 3
    titles = [i.title for i in items]
    assert "THYAO hisseleri günü yükselişle kapattı" in titles
    assert "THY filosuna yeni uçak katıldı" in titles
    assert "Kaynaksız haber başlığı" in titles


@pytest.mark.asyncio
@respx.mock
async def test_source_suffix_is_stripped_from_title():
    respx.route(host="news.google.com").mock(return_value=httpx.Response(200, text=_SAMPLE_RSS))
    provider = GoogleNewsProvider()

    items = await provider.get_news("THYAO", limit=15)
    first = next(i for i in items if i.source == "Mynet Finans")
    assert first.title == "THYAO hisseleri günü yükselişle kapattı"
    assert "Mynet Finans" not in first.title


@pytest.mark.asyncio
@respx.mock
async def test_item_without_source_tag_falls_back_gracefully():
    respx.route(host="news.google.com").mock(return_value=httpx.Response(200, text=_SAMPLE_RSS))
    provider = GoogleNewsProvider()

    items = await provider.get_news("THYAO", limit=15)
    fallback = next(i for i in items if i.title == "Kaynaksız haber başlığı")
    assert fallback.source == "Google Haberler"


@pytest.mark.asyncio
@respx.mock
async def test_limit_is_respected():
    respx.route(host="news.google.com").mock(return_value=httpx.Response(200, text=_SAMPLE_RSS))
    provider = GoogleNewsProvider()

    items = await provider.get_news("THYAO", limit=2)
    assert len(items) == 2


@pytest.mark.asyncio
@respx.mock
async def test_http_error_raises_provider_unavailable():
    respx.route(host="news.google.com").mock(side_effect=httpx.ConnectError("network down"))
    provider = GoogleNewsProvider()

    with pytest.raises(ProviderUnavailableError):
        await provider.get_news("THYAO")


@pytest.mark.asyncio
@respx.mock
async def test_malformed_xml_raises_provider_unavailable():
    respx.route(host="news.google.com").mock(return_value=httpx.Response(200, text="<not valid xml"))
    provider = GoogleNewsProvider()

    with pytest.raises(ProviderUnavailableError):
        await provider.get_news("THYAO")


@pytest.mark.asyncio
@respx.mock
async def test_market_news_uses_general_market_query():
    route = respx.route(host="news.google.com").mock(return_value=httpx.Response(200, text=_SAMPLE_RSS))
    provider = GoogleNewsProvider()

    items = await provider.get_market_news(limit=10)

    assert len(items) == 3
    requested_url = str(route.calls.last.request.url)
    assert "q=Borsa" in requested_url
