"""ADR-015 taxonomy extension: BIST-relevant yfinance industries."""

from __future__ import annotations

import pytest
from yfinance.const import SECTOR_INDUSTY_MAPPING

from app.providers.company.taxonomy import _INDUSTRY_TRANSLATIONS, _key, normalize_sector_industry

# Yahoo renamed this industry ("Marine Shipping" today); kept for profiles
# cached under the old name.
_LEGACY_YAHOO_INDUSTRIES = {"shipping & ports"}


def test_every_mapped_industry_is_a_real_yfinance_industry():
    known = {_key(industry) for industries in SECTOR_INDUSTY_MAPPING.values() for industry in industries}
    unknown = [k for k in _INDUSTRY_TRANSLATIONS if k not in _LEGACY_YAHOO_INDUSTRIES and _key(k) not in known]
    assert unknown == []


@pytest.mark.parametrize(
    ("industry", "expected"),
    [
        ("Textile Manufacturing", ("Sanayi", "Tekstil")),
        ("Engineering & Construction", ("Sanayi", "İnşaat")),
        ("Residential Construction", ("Sanayi", "İnşaat")),
        ("Aerospace & Defense", ("Sanayi", "Savunma Elektroniği")),
        ("Apparel Retail", ("Perakende", "Giyim Perakendesi")),
        ("Specialty Retail", ("Perakende", "Perakende")),
        ("Specialty Chemicals", ("Sanayi", "Kimya")),
        ("Paper & Paper Products", ("Sanayi", "Kağıt")),
        ("Building Materials", ("Sanayi", "Çimento ve Yapı Malzemeleri")),
        ("Packaging & Containers", ("Sanayi", "Ambalaj")),
        ("Utilities - Renewable", ("Enerji", "Elektrik Üretim")),
        ("Utilities - Diversified", ("Enerji", "Elektrik Üretim")),
        ("Utilities - Regulated Electric", ("Enerji", "Elektrik Dağıtım")),
        ("Travel Services", ("Hizmetler", "Turizm ve Eğlence")),
        ("Lodging", ("Hizmetler", "Turizm ve Eğlence")),
        ("Information Technology Services", ("Teknoloji", "Bilişim Hizmetleri")),
        ("Software - Application", ("Teknoloji", "Yazılım")),
        ("Insurance - Property & Casualty", ("Finans", "Sigorta")),
        ("Real Estate - Development", ("Gayrimenkul", "GYO")),
        ("Financial Conglomerates", ("Holding", "Holding")),
        ("Conglomerates", ("Holding", "Holding")),
        ("Farm Products", ("Gıda ve İçecek", "Gıda")),
        ("Beverages - Wineries & Distilleries", ("Gıda ve İçecek", "İçecek")),
        ("Auto Parts", ("Sanayi", "Otomotiv")),
        ("Airlines", ("Ulaştırma", "Havayolu")),
        ("Airports & Air Services", ("Ulaştırma", "Havalimanı ve Yer Hizmetleri")),
        ("Marine Shipping", ("Ulaştırma", "Denizcilik")),
        ("Capital Markets", ("Finans", "Aracı Kurum")),
        ("Oil & Gas Integrated", ("Enerji", "Petrol ve Doğalgaz")),
    ],
)
def test_bist_relevant_industries_translate(industry, expected):
    assert normalize_sector_industry("Ignored Sector", industry) == expected


@pytest.mark.parametrize(
    "variant",
    ["Oil & Gas E&P", "Oil Gas E P", "oil & gas e&p", "  OIL & GAS E&P  "],
)
def test_punctuation_and_case_variants_match(variant):
    assert normalize_sector_industry("Energy", variant) == ("Enerji", "Petrol ve Doğalgaz")


def test_dash_variants_of_new_entries_match():
    expected = ("Enerji", "Elektrik Dağıtım")
    assert normalize_sector_industry("Utilities", "Utilities—Regulated Electric") == expected
    assert normalize_sector_industry("Utilities", "Utilities Regulated Electric") == expected


def test_unknown_industries_still_pass_through_unchanged():
    assert normalize_sector_industry("Consumer Cyclical", "Luxury Goods") == ("Perakende", "Luxury Goods")
    assert normalize_sector_industry("Mystery", "Shell Companies") == ("Mystery", "Shell Companies")
