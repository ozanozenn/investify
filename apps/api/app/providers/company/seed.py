"""Static seed for the initial validation companies (roadmap section 90).

This is NOT meant to become the way all ~500 BIST companies are onboarded —
that would violate section 3.2 ("Bütün BIST şirketlerini manuel hardcode
etme"). It exists so `docker compose up` immediately recognizes a handful of
well-known tickers with curated sector/industry/description metadata even
if `yfinance`'s own `sector`/`industry`/`longBusinessSummary` fields are
sparse for a given company at bootstrap time. Any ticker NOT in this seed is
still resolvable — `providers/company/yfinance_company_provider.py` falls
back to live `yfinance` profile data with only a sector name (no fixed
seed entry required). See docs/PHASE_1_SCOPE.md 3.2 for the strategy.
"""

from __future__ import annotations

SEED_COMPANIES: dict[str, dict] = {
    "THYAO": {
        "name": "Türk Hava Yolları A.O.",
        "sector": "Ulaştırma",
        "industry": "Havayolu",
        "is_financial_industry": False,
        "kap_url": "https://www.kap.org.tr/tr/sirket-bilgileri/ozet/1107-turk-hava-yollari-a-o",
        "website": "https://www.turkishairlines.com",
    },
    "ASELS": {
        "name": "Aselsan Elektronik Sanayi ve Ticaret A.Ş.",
        "sector": "Sanayi",
        "industry": "Savunma Elektroniği",
        "is_financial_industry": False,
        "kap_url": "https://www.kap.org.tr/tr/sirket-bilgileri/ozet",
        "website": "https://www.aselsan.com.tr",
    },
    "FROTO": {
        "name": "Ford Otomotiv Sanayi A.Ş.",
        "sector": "Sanayi",
        "industry": "Otomotiv",
        "is_financial_industry": False,
        "kap_url": "https://www.kap.org.tr/tr/sirket-bilgileri/ozet",
        "website": "https://www.fordotosan.com.tr",
    },
    "TUPRS": {
        "name": "Türkiye Petrol Rafinerileri A.Ş.",
        "sector": "Enerji",
        "industry": "Petrol Rafinaj",
        "is_financial_industry": False,
        "kap_url": "https://www.kap.org.tr/tr/sirket-bilgileri/ozet",
        "website": "https://www.tupras.com.tr",
    },
    "GARAN": {
        "name": "Türkiye Garanti Bankası A.Ş.",
        "sector": "Finans",
        "industry": "Bankacılık",
        "is_financial_industry": True,
        "kap_url": "https://www.kap.org.tr/tr/sirket-bilgileri/ozet",
        "website": "https://www.garantibbvainvestorrelations.com",
    },
    "AKBNK": {
        "name": "Akbank T.A.Ş.",
        "sector": "Finans",
        "industry": "Bankacılık",
        "is_financial_industry": True,
        "kap_url": "https://www.kap.org.tr/tr/sirket-bilgileri/ozet",
        "website": "https://www.akbankinvestorrelations.com",
    },
    "SISE": {
        "name": "Türkiye Şişe ve Cam Fabrikaları A.Ş.",
        "sector": "Sanayi",
        "industry": "Cam",
        "is_financial_industry": False,
        "kap_url": "https://www.kap.org.tr/tr/sirket-bilgileri/ozet",
        "website": "https://www.sisecam.com.tr",
    },
    "EREGL": {
        "name": "Ereğli Demir ve Çelik Fabrikaları T.A.Ş.",
        "sector": "Sanayi",
        "industry": "Demir Çelik",
        "is_financial_industry": False,
        "kap_url": "https://www.kap.org.tr/tr/sirket-bilgileri/ozet",
        "website": "https://www.erdemir.com.tr",
    },
}
