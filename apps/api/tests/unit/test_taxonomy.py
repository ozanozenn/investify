from app.providers.company.taxonomy import normalize_sector_industry


def test_yfinance_airline_maps_to_seed_taxonomy():
    # PGSUS's live yfinance profile vs THYAO's curated seed should land on
    # the same canonical (sector, industry) so peer comparison can match them.
    assert normalize_sector_industry("Industrials", "Airlines") == ("Ulaştırma", "Havayolu")


def test_seed_values_pass_through_unchanged():
    assert normalize_sector_industry("Ulaştırma", "Havayolu") == ("Ulaştırma", "Havayolu")


def test_unmapped_industry_with_mapped_sector_translates_sector_only():
    # "Steel" has no direct industry mapping override needed here, but pick
    # an industry with no entry and a sector that IS mapped, to prove the
    # sector-level fallback fires and the industry string is left untouched.
    sector, industry = normalize_sector_industry("Industrials", "Some New Industrial Niche")
    assert sector == "Sanayi"
    assert industry == "Some New Industrial Niche"  # never invented, passed through as-is


def test_unmapped_sector_and_industry_pass_through_unchanged():
    assert normalize_sector_industry("Some New Sector", "Some New Industry") == (
        "Some New Sector",
        "Some New Industry",
    )


def test_missing_values_default_to_diger():
    sector, industry = normalize_sector_industry(None, None)
    assert sector == "Diğer"
    assert industry == "Diğer"


def test_bank_variants_both_map_to_same_canonical_pair():
    assert normalize_sector_industry("Financial Services", "Banks—Regional") == ("Finans", "Bankacılık")
    assert normalize_sector_industry("Financial Services", "Banks - Diversified") == ("Finans", "Bankacılık")
