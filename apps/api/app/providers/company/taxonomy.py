"""Sector/industry taxonomy normalization (Phase 2 fix for the gap recorded
in docs/TECHNICAL_DEBT.md "Phase 2 additions").

`providers/company/seed.py` hand-curates Turkish sector/industry labels for
a handful of validation tickers (e.g. THYAO: sector="Ulaştırma",
industry="Havayolu"). Every other ticker bootstraps via live `yfinance`,
which returns its own English, Yahoo/GICS-style taxonomy (e.g. PGSUS:
sector="Industrials", industry="Airlines"). Because
`services/company_bootstrap.py` groups companies (and therefore peer
comparison) by an EXACT string match on `Industry.name`/`Sector.name`, two
real-world peers never matched purely because their taxonomy source
differed — verified live: THYAO vs PGSUS produced zero peers despite both
being real BIST airlines.

This module translates yfinance's raw (sector, industry) strings into the
same canonical Turkish taxonomy the seed uses, keyed primarily by
`industry` (more specific and less ambiguous than `sector` alone — e.g.
"Airlines" always implies transportation regardless of which broad sector
bucket Yahoo files it under). Deliberately NOT exhaustive — mirrors
`providers/company/ticker_index.py`'s own "not exhaustive, extend as
needed" philosophy. An unmapped (sector, industry) pair is passed through
UNCHANGED (never guessed/invented) — this does not regress anything: two
live-bootstrapped companies sharing the same unmapped English string still
match each other exactly as before, only cross-taxonomy (seed vs live)
matching improves for the industries listed here.
"""

from __future__ import annotations

import re

# yfinance `industry` string -> canonical (sector, industry). Matching is
# case- and punctuation-insensitive (see `_key`): "Banks—Regional",
# "Banks - Regional" and yfinance's own de-punctuated "Banks Regional" are
# the same key. Populated from the seed set's own industries plus other
# industries realistically expected among BIST names; the ADR-015 block
# below uses only industry names that appear in yfinance's
# `yfinance.const.SECTOR_INDUSTY_MAPPING` (checked by tests).
_INDUSTRY_TRANSLATIONS: dict[str, tuple[str, str]] = {
    "airlines": ("Ulaştırma", "Havayolu"),
    "aerospace & defense": ("Sanayi", "Savunma Elektroniği"),
    "banks—regional": ("Finans", "Bankacılık"),
    "banks—diversified": ("Finans", "Bankacılık"),
    "banks - regional": ("Finans", "Bankacılık"),
    "banks - diversified": ("Finans", "Bankacılık"),
    "steel": ("Sanayi", "Demir Çelik"),
    "auto manufacturers": ("Sanayi", "Otomotiv"),
    "auto parts": ("Sanayi", "Otomotiv"),
    "oil & gas refining & marketing": ("Enerji", "Petrol Rafinaj"),
    "specialty chemicals": ("Sanayi", "Kimya"),
    "chemicals": ("Sanayi", "Kimya"),
    "agricultural inputs": ("Sanayi", "Tarım Kimyasalları"),
    "packaged foods": ("Gıda ve İçecek", "Gıda"),
    "confectioners": ("Gıda ve İçecek", "Gıda"),
    "beverages—non-alcoholic": ("Gıda ve İçecek", "İçecek"),
    "beverages - non-alcoholic": ("Gıda ve İçecek", "İçecek"),
    "beverages—brewers": ("Gıda ve İçecek", "İçecek"),
    "beverages - brewers": ("Gıda ve İçecek", "İçecek"),
    "grocery stores": ("Perakende", "Perakende"),
    "discount stores": ("Perakende", "Perakende"),
    "telecom services": ("Telekomünikasyon", "Telekomünikasyon"),
    "conglomerates": ("Holding", "Holding"),
    # Mostly cement producers on BIST (glass has no Yahoo industry of its
    # own); was "Cam", which made every cement company a peer of SISE.
    "building materials": ("Sanayi", "Çimento ve Yapı Malzemeleri"),
    "gold": ("Madencilik", "Madencilik"),
    "copper": ("Madencilik", "Madencilik"),
    "other industrial metals & mining": ("Madencilik", "Madencilik"),
    "real estate—diversified": ("Gayrimenkul", "GYO"),
    "real estate - diversified": ("Gayrimenkul", "GYO"),
    "reit—diversified": ("Gayrimenkul", "GYO"),
    "reit - diversified": ("Gayrimenkul", "GYO"),
    "utilities—renewable": ("Enerji", "Elektrik Üretim"),
    "utilities - renewable": ("Enerji", "Elektrik Üretim"),
    "utilities—independent power producers": ("Enerji", "Elektrik Üretim"),
    "utilities - independent power producers": ("Enerji", "Elektrik Üretim"),
    "insurance—diversified": ("Finans", "Sigorta"),
    "insurance - diversified": ("Finans", "Sigorta"),
    "insurance—life": ("Finans", "Sigorta"),
    "insurance - life": ("Finans", "Sigorta"),
    "software—application": ("Teknoloji", "Yazılım"),
    "software - application": ("Teknoloji", "Yazılım"),
    "software—infrastructure": ("Teknoloji", "Yazılım"),
    "software - infrastructure": ("Teknoloji", "Yazılım"),
    "semiconductors": ("Teknoloji", "Elektronik"),
    "electronic components": ("Teknoloji", "Elektronik"),
    "drug manufacturers—general": ("Sağlık", "İlaç"),
    "drug manufacturers - general": ("Sağlık", "İlaç"),
    "drug manufacturers—specialty & generic": ("Sağlık", "İlaç"),
    "drug manufacturers - specialty & generic": ("Sağlık", "İlaç"),
    "medical devices": ("Sağlık", "Medikal Cihaz"),
    "textile manufacturing": ("Sanayi", "Tekstil"),
    "apparel manufacturing": ("Sanayi", "Tekstil"),
    "paper & paper products": ("Sanayi", "Kağıt"),
    "furnishings, fixtures & appliances": ("Sanayi", "Dayanıklı Tüketim"),
    "leisure": ("Hizmetler", "Turizm ve Eğlence"),
    "resorts & casinos": ("Hizmetler", "Turizm ve Eğlence"),
    "lodging": ("Hizmetler", "Turizm ve Eğlence"),
    "advertising agencies": ("Hizmetler", "Medya"),
    "broadcasting": ("Hizmetler", "Medya"),
    "publishing": ("Hizmetler", "Medya"),
    "shipping & ports": ("Ulaştırma", "Denizcilik"),
    "railroads": ("Ulaştırma", "Demiryolu"),
    "trucking": ("Ulaştırma", "Kara Taşımacılığı"),
    "engineering & construction": ("Sanayi", "İnşaat"),
    # --- ADR-015 additions (Yahoo display names; variants via `_key`) ---
    # Basic Materials / Energy
    "lumber & wood production": ("Sanayi", "Orman Ürünleri"),
    "aluminum": ("Sanayi", "Alüminyum"),
    "silver": ("Madencilik", "Madencilik"),
    "other precious metals & mining": ("Madencilik", "Madencilik"),
    "coking coal": ("Madencilik", "Madencilik"),
    "thermal coal": ("Madencilik", "Madencilik"),
    "oil & gas integrated": ("Enerji", "Petrol ve Doğalgaz"),
    "oil & gas e&p": ("Enerji", "Petrol ve Doğalgaz"),
    "oil & gas midstream": ("Enerji", "Petrol ve Doğalgaz"),
    "oil & gas drilling": ("Enerji", "Petrol ve Doğalgaz"),
    "oil & gas equipment & services": ("Enerji", "Petrol ve Doğalgaz"),
    "solar": ("Enerji", "Güneş Enerjisi Ekipmanları"),
    # Utilities (energy generation / distribution)
    "utilities - diversified": ("Enerji", "Elektrik Üretim"),
    "utilities - regulated electric": ("Enerji", "Elektrik Dağıtım"),
    "utilities - regulated gas": ("Enerji", "Doğalgaz Dağıtım"),
    # Consumer Cyclical (retail, textiles, construction, tourism, packaging)
    "apparel retail": ("Perakende", "Giyim Perakendesi"),
    "department stores": ("Perakende", "Perakende"),
    "specialty retail": ("Perakende", "Perakende"),
    "home improvement retail": ("Perakende", "Perakende"),
    "internet retail": ("Perakende", "Perakende"),
    "auto & truck dealerships": ("Perakende", "Otomotiv Ticareti"),
    "footwear & accessories": ("Sanayi", "Tekstil"),
    "packaging & containers": ("Sanayi", "Ambalaj"),
    "residential construction": ("Sanayi", "İnşaat"),
    "travel services": ("Hizmetler", "Turizm ve Eğlence"),
    "restaurants": ("Hizmetler", "Restoran"),
    # Consumer Defensive (food, beverages, education)
    "beverages - wineries & distilleries": ("Gıda ve İçecek", "İçecek"),
    "farm products": ("Gıda ve İçecek", "Gıda"),
    "food distribution": ("Gıda ve İçecek", "Gıda"),
    "education & training services": ("Hizmetler", "Eğitim"),
    # Communication Services / Technology
    "entertainment": ("Hizmetler", "Medya"),
    "internet content & information": ("Teknoloji", "İnternet Hizmetleri"),
    "information technology services": ("Teknoloji", "Bilişim Hizmetleri"),
    "communication equipment": ("Teknoloji", "Haberleşme Ekipmanları"),
    "computer hardware": ("Teknoloji", "Bilgisayar Donanımı"),
    "electronics & computer distribution": ("Teknoloji", "Bilişim Dağıtımı"),
    "scientific & technical instruments": ("Teknoloji", "Elektronik"),
    "semiconductor equipment & materials": ("Teknoloji", "Elektronik"),
    "consumer electronics": ("Sanayi", "Dayanıklı Tüketim"),
    # Financial Services (insurance, brokers, leasing/factoring, holdings)
    "insurance - property & casualty": ("Finans", "Sigorta"),
    "insurance - reinsurance": ("Finans", "Sigorta"),
    "insurance - specialty": ("Finans", "Sigorta"),
    "insurance brokers": ("Finans", "Sigorta"),
    "capital markets": ("Finans", "Aracı Kurum"),
    "asset management": ("Finans", "Varlık Yönetimi"),
    "credit services": ("Finans", "Finansman ve Faktoring"),
    "mortgage finance": ("Finans", "Finansman ve Faktoring"),
    "financial conglomerates": ("Holding", "Holding"),
    # Healthcare
    "medical care facilities": ("Sağlık", "Hastane ve Sağlık Hizmetleri"),
    "medical instruments & supplies": ("Sağlık", "Medikal Cihaz"),
    "medical distribution": ("Sağlık", "Medikal Dağıtım"),
    # Industrials (defense/aerospace and engineering already above)
    "airports & air services": ("Ulaştırma", "Havalimanı ve Yer Hizmetleri"),
    "marine shipping": ("Ulaştırma", "Denizcilik"),
    "integrated freight & logistics": ("Ulaştırma", "Lojistik"),
    "building products & equipment": ("Sanayi", "Yapı Ürünleri"),
    "electrical equipment & parts": ("Sanayi", "Elektrikli Ekipman"),
    "farm & heavy construction machinery": ("Sanayi", "Makine"),
    "specialty industrial machinery": ("Sanayi", "Makine"),
    "metal fabrication": ("Sanayi", "Metal Eşya"),
    "industrial distribution": ("Hizmetler", "Endüstriyel Dağıtım"),
    "infrastructure operations": ("Hizmetler", "Altyapı İşletmeciliği"),
    "waste management": ("Hizmetler", "Çevre Hizmetleri"),
    "pollution & treatment controls": ("Hizmetler", "Çevre Hizmetleri"),
    "security & protection services": ("Hizmetler", "Güvenlik Hizmetleri"),
    # Real Estate (BIST real-estate companies are overwhelmingly GYOs)
    "real estate - development": ("Gayrimenkul", "GYO"),
    "real estate services": ("Gayrimenkul", "Gayrimenkul Hizmetleri"),
    "reit - retail": ("Gayrimenkul", "GYO"),
    "reit - office": ("Gayrimenkul", "GYO"),
    "reit - residential": ("Gayrimenkul", "GYO"),
    "reit - industrial": ("Gayrimenkul", "GYO"),
    "reit - hotel & motel": ("Gayrimenkul", "GYO"),
    "reit - specialty": ("Gayrimenkul", "GYO"),
}

# yfinance `sector` string (case-insensitive) -> canonical Turkish sector,
# used only as a fallback when `industry` has no entry above (still keeps
# the yfinance industry string as-is, since we have nothing better to
# translate it to).
_SECTOR_TRANSLATIONS: dict[str, str] = {
    "industrials": "Sanayi",
    "financial services": "Finans",
    "financials": "Finans",
    "energy": "Enerji",
    "basic materials": "Sanayi",
    "real estate": "Gayrimenkul",
    "communication services": "Telekomünikasyon",
    "consumer defensive": "Gıda ve İçecek",
    "consumer cyclical": "Perakende",
    "utilities": "Enerji",
    "technology": "Teknoloji",
    "healthcare": "Sağlık",
}


def _key(text: str) -> str:
    """Case/punctuation-insensitive lookup key: "Oil & Gas E&P",
    "Banks—Regional" and "Banks - Regional" -> "oil gas e p", "banks regional"."""
    return " ".join(re.findall(r"\w+", text.lower()))


_INDUSTRY_LOOKUP: dict[str, tuple[str, str]] = {_key(k): v for k, v in _INDUSTRY_TRANSLATIONS.items()}
_SECTOR_LOOKUP: dict[str, str] = {_key(k): v for k, v in _SECTOR_TRANSLATIONS.items()}


def normalize_sector_industry(sector: str | None, industry: str | None) -> tuple[str, str]:
    """Best-effort translation into the canonical (Turkish) taxonomy used by
    `providers/company/seed.py`. Falls through to the original strings
    unchanged wherever no mapping exists — never invents a label."""
    sector = sector or "Diğer"
    industry = industry or sector

    industry_key = _key(industry)
    if industry_key in _INDUSTRY_LOOKUP:
        return _INDUSTRY_LOOKUP[industry_key]

    sector_key = _key(sector)
    if sector_key in _SECTOR_LOOKUP:
        return _SECTOR_LOOKUP[sector_key], industry

    return sector, industry
