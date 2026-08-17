"""Static ticker -> name index powering `/companies/search` autocomplete
only (roadmap section 34). This is NOT company financial data and is not
the mechanism used to onboard a company's full profile (that is
`CompanyDataProvider`, see seed.py / yfinance_company_provider.py) — it
exists purely so typing "THY" can suggest "THYAO" without a network call.
Deliberately not exhaustive (~60 large/liquid BIST tickers); any ticker
typed exactly (e.g. a smaller-cap symbol not listed here) still resolves
fine through `/companies/{ticker}` because that path bootstraps via the
live provider regardless of whether it appears in this index.
"""

from __future__ import annotations

TICKER_INDEX: dict[str, str] = {
    "THYAO": "Türk Hava Yolları A.O.",
    "ASELS": "Aselsan Elektronik Sanayi ve Ticaret A.Ş.",
    "FROTO": "Ford Otomotiv Sanayi A.Ş.",
    "TUPRS": "Türkiye Petrol Rafinerileri A.Ş.",
    "GARAN": "Türkiye Garanti Bankası A.Ş.",
    "AKBNK": "Akbank T.A.Ş.",
    "SISE": "Türkiye Şişe ve Cam Fabrikaları A.Ş.",
    "EREGL": "Ereğli Demir ve Çelik Fabrikaları T.A.Ş.",
    "BIMAS": "BİM Birleşik Mağazalar A.Ş.",
    "KCHOL": "Koç Holding A.Ş.",
    "SAHOL": "Hacı Ömer Sabancı Holding A.Ş.",
    "TCELL": "Turkcell İletişim Hizmetleri A.Ş.",
    "TTKOM": "Türk Telekomünikasyon A.Ş.",
    "YKBNK": "Yapı ve Kredi Bankası A.Ş.",
    "ISCTR": "Türkiye İş Bankası A.Ş.",
    "HALKB": "Türkiye Halk Bankası A.Ş.",
    "VAKBN": "Türkiye Vakıflar Bankası T.A.O.",
    "PGSUS": "Pegasus Hava Taşımacılığı A.Ş.",
    "TAVHL": "TAV Havalimanları Holding A.Ş.",
    "TOASO": "Tofaş Türk Otomobil Fabrikası A.Ş.",
    "OTKAR": "Otokar Otomotiv ve Savunma Sanayi A.Ş.",
    "ARCLK": "Arçelik A.Ş.",
    "VESTL": "Vestel Elektronik Sanayi ve Ticaret A.Ş.",
    "SASA": "SASA Polyester Sanayi A.Ş.",
    "HEKTS": "Hektaş Ticaret A.Ş.",
    "GUBRF": "Gübre Fabrikaları T.A.Ş.",
    "PETKM": "Petkim Petrokimya Holding A.Ş.",
    "KOZAL": "Koza Altın İşletmeleri A.Ş.",
    "KOZAA": "Koza Anadolu Metal Madencilik A.Ş.",
    "EKGYO": "Emlak Konut Gayrimenkul Yatırım Ortaklığı A.Ş.",
    "ENKAI": "Enka İnşaat ve Sanayi A.Ş.",
    "TKFEN": "Tekfen Holding A.Ş.",
    "MGROS": "Migros Ticaret A.Ş.",
    "SOKM": "Şok Marketler Ticaret A.Ş.",
    "CCOLA": "Coca-Cola İçecek A.Ş.",
    "AEFES": "Anadolu Efes Biracılık ve Malt Sanayii A.Ş.",
    "ULKER": "Ülker Bisküvi Sanayi A.Ş.",
    "DOAS": "Doğuş Otomotiv Servis ve Ticaret A.Ş.",
    "ISDMR": "İskenderun Demir ve Çelik A.Ş.",
    "KRDMD": "Kardemir Karabük Demir Çelik Sanayi ve Ticaret A.Ş.",
    "TSKB": "Türkiye Sınai Kalkınma Bankası A.Ş.",
    "SISECAM": "Türkiye Şişe ve Cam Fabrikaları A.Ş.",
    "ALARK": "Alarko Holding A.Ş.",
    "AKSA": "Aksa Akrilik Kimya Sanayii A.Ş.",
    "AKSEN": "Aksa Enerji Üretim A.Ş.",
    "ODAS": "Odaş Elektrik Üretim Sanayi Ticaret A.Ş.",
    "ZOREN": "Zorlu Enerji Elektrik Üretim A.Ş.",
    "TTRAK": "Türk Traktör ve Ziraat Makineleri A.Ş.",
    "CIMSA": "Çimsa Çimento Sanayi ve Ticaret A.Ş.",
    "OYAKC": "Oyak Çimento Fabrikaları A.Ş.",
    "TAVFO": "TAV Havalimanları Holding A.Ş.",
    "MAVI": "Mavi Giyim Sanayi ve Ticaret A.Ş.",
    "LOGO": "Logo Yazılım Sanayi ve Ticaret A.Ş.",
    "NETAS": "Netaş Telekomünikasyon A.Ş.",
    "KONTR": "Kontrolmatik Teknoloji Enerji ve Mühendislik A.Ş.",
    "SMRTG": "Smart Güneş Enerjisi Teknolojileri A.Ş.",
    "ASTOR": "Astor Enerji A.Ş.",
    "BRSAN": "Borusan Boru Sanayi Ticaret ve Dış Ticaret A.Ş.",
    "BRISA": "Brisa Bridgestone Sabancı Lastik Sanayi ve Ticaret A.Ş.",
    "GOLTS": "Göltaş Göller Bölgesi Çimento Sanayi ve Ticaret A.Ş.",
    "TABGD": "Tab Gıda Sanayi ve Ticaret A.Ş.",
}


def search_tickers(query: str, limit: int = 10) -> list[dict]:
    q = query.strip().upper()
    if not q:
        return []
    starts_with = [(t, n) for t, n in TICKER_INDEX.items() if t.startswith(q)]
    contains = [
        (t, n) for t, n in TICKER_INDEX.items() if q not in [s for s, _ in starts_with] and (q in t or q in n.upper())
    ]
    ordered = starts_with + [pair for pair in contains if pair not in starts_with]
    return [{"ticker": t, "name": n} for t, n in ordered[:limit]]
