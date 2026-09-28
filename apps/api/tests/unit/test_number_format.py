from __future__ import annotations

from app.llm.number_format import (
    extract_number_candidates,
    format_currency,
    format_multiple,
    format_percent_points,
    format_price,
    format_ratio_percent,
    format_score,
)


def test_format_ratio_percent_matches_real_ebitda_growth_example():
    assert format_ratio_percent(0.8259859533087344) == "%82,6"


def test_format_ratio_percent_negative_puts_sign_before_percent_sign():
    assert format_ratio_percent(-0.059) == "-%5,9"


def test_format_percent_points_for_tcmb_policy_rate():
    assert format_percent_points(37.0) == "%37,0"


def test_format_currency_uses_milyar_tier():
    assert format_currency(48901969000.0) == "48,9 milyar TL"


def test_format_currency_negative_amount():
    assert format_currency(-10733502000.0) == "-10,7 milyar TL"


def test_format_currency_small_amount_stays_plain():
    assert format_currency(842.5) == "842,50 TL"


def test_format_multiple_matches_real_pe_example():
    assert format_multiple(56.67737461756061) == "56,7x"


def test_format_price_two_decimals():
    assert format_price(125.4) == "125,40 TL"


def test_format_score():
    assert format_score(66.5) == "66,5/100"


def test_extract_grouped_thousands_number_as_single_token():
    # This is the exact real-world case that slipped through the old regex:
    # a large Turkish-formatted TRY amount must be read as ONE number, not
    # fragments split at each thousands separator.
    results = extract_number_candidates("Şirketin serbest nakit akışı 10.733.502.000 TL seviyesindedir.")
    literals = [literal for literal, _ in results]
    assert "10.733.502.000" in literals
    values = dict(results)["10.733.502.000"]
    assert values == [10733502000.0]


def test_extract_negative_grouped_thousands_preserves_sign():
    results = extract_number_candidates("SNA -10.733.502.000 TL olarak gerçekleşmiştir.")
    values = dict(results)["-10.733.502.000"]
    assert values == [-10733502000.0]


def test_extract_percent_gives_both_ratio_and_point_scale_candidates():
    results = extract_number_candidates("FAVÖK büyümesi %82,6 seviyesindedir.")
    values = dict(results)["82,6"]
    assert values == [0.826, 82.6]


def test_extract_leading_sign_before_percent_symbol():
    results = extract_number_candidates("FCF marjı -%6,0 seviyesinde daralmıştır.")
    values = dict(results)["6,0"]
    assert values == [-0.06, -6.0]


def test_extract_multiple_suffix():
    results = extract_number_candidates("F/K oranı 56,7x seviyesindedir.")
    values = dict(results)["56,7"]
    assert values == [56.7]


def test_extract_currency_suffix_scales_to_absolute_value():
    results = extract_number_candidates("Piyasa değeri 48,9 milyar TL civarındadır.")
    values = dict(results)["48,9"]
    assert values == [48_900_000_000.0]


def test_extract_small_decimal_with_leading_zero_is_not_misread_as_grouped():
    results = extract_number_candidates("Oran 0,264 seviyesindedir.")
    values = dict(results)["0,264"]
    assert values == [0.264]


def test_extract_calendar_year_like_plain_number():
    results = extract_number_candidates("2026 yılında büyüme bekleniyor.")
    values = dict(results)["2026"]
    assert values == [2026.0]
