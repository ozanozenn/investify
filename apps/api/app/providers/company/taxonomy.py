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

# yfinance `industry` string (case-insensitive) -> canonical (sector, industry).
# Populated from the seed set's own industries plus other industries
# realistically expected among BIST large/liquid names.
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
    "building materials": ("Sanayi", "Cam"),
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
}


def normalize_sector_industry(sector: str | None, industry: str | None) -> tuple[str, str]:
    """Best-effort translation into the canonical (Turkish) taxonomy used by
    `providers/company/seed.py`. Falls through to the original strings
    unchanged wherever no mapping exists — never invents a label."""
    sector = sector or "Diğer"
    industry = industry or sector

    industry_key = industry.strip().lower()
    if industry_key in _INDUSTRY_TRANSLATIONS:
        return _INDUSTRY_TRANSLATIONS[industry_key]

    sector_key = sector.strip().lower()
    if sector_key in _SECTOR_TRANSLATIONS:
        return _SECTOR_TRANSLATIONS[sector_key], industry

    return sector, industry
