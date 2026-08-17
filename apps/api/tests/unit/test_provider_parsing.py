from app.models.enums import CanonicalField, DisclosureCategory
from app.providers.disclosure.kap_provider import _parse_kap_datetime, categorize
from app.providers.financial.yfinance_mapping import INCOME_STATEMENT_MAP, extract


def test_extract_prefers_first_matching_candidate_label():
    row_map = {CanonicalField.REVENUE: ["Total Revenue", "Operating Revenue"]}
    statement_index = ["Operating Revenue", "Total Revenue"]
    column = {"Total Revenue": 1000.0, "Operating Revenue": 900.0}
    result = extract(row_map, statement_index, column)
    assert result["REVENUE"] == 1000.0  # first candidate in the list wins


def test_extract_skips_nan_and_missing_rows():
    column = {"Total Revenue": float("nan")}
    result = extract(INCOME_STATEMENT_MAP, ["Total Revenue"], column)
    assert "REVENUE" not in result  # NaN is not a usable value


def test_extract_falls_back_to_second_candidate_when_first_absent():
    row_map = {CanonicalField.EBIT: ["EBIT", "Operating Income"]}
    column = {"Operating Income": 42.0}
    result = extract(row_map, ["Operating Income"], column)
    assert result["EBIT"] == 42.0


def test_kap_categorize_matches_known_keywords():
    assert categorize("2025 Yılı Kar Payı Dağıtım Teklifi") == DisclosureCategory.DIVIDEND
    assert categorize("Yönetim Kurulu Kararı") == DisclosureCategory.MANAGEMENT
    assert categorize("Finansal Rapor - Bağımsız Denetim") == DisclosureCategory.FINANCIAL_RESULT
    assert categorize(None) == DisclosureCategory.OTHER
    assert categorize("tamamen alakasız bir başlık") == DisclosureCategory.OTHER


def test_kap_datetime_parsing_converts_istanbul_to_utc():
    parsed = _parse_kap_datetime("17.08.2026 18:12:42")
    assert parsed.utcoffset().total_seconds() == 0
    assert parsed.hour == 15  # 18:12 TRT (UTC+3) -> 15:12 UTC
