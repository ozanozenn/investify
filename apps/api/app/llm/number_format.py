"""Human-readable Turkish number formatting for LLM prompt context, and the
matching parser the hallucination guard uses to read numbers back out of
the LLM's free text.

Why both directions live in one module: the guard can only verify a number
the LLM wrote if it can parse it back into the same scale the formatter
produced. Keeping format/parse next to each other means a new format style
can't be added without updating the parser that has to undo it.
"""

from __future__ import annotations

import re

_TR_LOCALE_DECIMAL = ","
_TR_LOCALE_THOUSANDS = "."


def _tr_number(value: float, decimals: int) -> str:
    """Plain Turkish-locale grouped number, e.g. 48901969000.0 -> "48.901.969.000"."""
    formatted = f"{value:,.{decimals}f}"
    # f-string grouping uses US convention (, thousands . decimal) — swap to Turkish.
    return formatted.translate(str.maketrans({",": "", ".": ","})).translate({0x0001: "."})


def _signed_percent(points: float, decimals: int) -> str:
    # Turkish convention puts the sign before the "%", e.g. "-%5,9", not "%-5,9".
    sign = "-" if points < 0 else ""
    return f"{sign}%{_tr_number(abs(points), decimals)}"


def format_ratio_percent(value: float, decimals: int = 1) -> str:
    """A 0-1 scale ratio (e.g. growth rates, margins) -> "%82,6"."""
    return _signed_percent(value * 100, decimals)


def format_percent_points(value: float, decimals: int = 1) -> str:
    """A value already expressed in percentage points (e.g. TCMB policy
    rate stored as 37.0 meaning 37%) -> "%37,0"."""
    return _signed_percent(value, decimals)


def format_multiple(value: float, decimals: int = 1) -> str:
    """A ratio/multiple such as P/E or Net Debt/EBITDA -> "56,7x"."""
    return f"{_tr_number(value, decimals)}x"


_CURRENCY_TIERS: list[tuple[float, float, str]] = [
    (1_000_000_000, 1_000_000_000, "milyar"),
    (1_000_000, 1_000_000, "milyon"),
    (1_000, 1_000, "bin"),
]


def format_currency(value: float, currency: str = "TL", decimals: int = 1) -> str:
    """A large absolute TRY amount -> compact "48,9 milyar TL"; small
    amounts (e.g. a per-share price) stay plain, e.g. "125,40 TL"."""
    magnitude = abs(value)
    for threshold, divisor, label in _CURRENCY_TIERS:
        if magnitude >= threshold:
            return f"{_tr_number(value / divisor, decimals)} {label} {currency}"
    return f"{_tr_number(value, 2)} {currency}"


def format_price(value: float, currency: str = "TL", decimals: int = 2) -> str:
    """A per-share / per-unit price — never compacted into milyar/milyon."""
    return f"{_tr_number(value, decimals)} {currency}"


def format_score(value: float, decimals: int = 1) -> str:
    """A 0-100 deterministic score -> "66,5/100"."""
    return f"{_tr_number(value, decimals)}/100"


def format_plain(value: float, decimals: int = 2) -> str:
    """Fallback for numeric fields with no more specific semantic style."""
    return _tr_number(value, decimals)


# --- Parsing (guard side) ---------------------------------------------------

# Turkish-grouped integer, optionally with a Turkish decimal comma:
# "10.733.502.000" or "48.901.969.000,50".
_TR_GROUPED_RE = r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?"
# US-grouped integer, optionally with a US decimal point (in case an LLM
# slips into this convention despite instructions):
# "10,733,502,000" or "10,733,502,000.50".
_US_GROUPED_RE = r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?"
# A simple Turkish decimal: "82,6". Must not itself look like a grouped
# number (handled by trying the grouped patterns first).
_TR_DECIMAL_RE = r"-?\d+,\d+"
# Plain integer or US-style decimal: "82.6" or "100".
_PLAIN_RE = r"-?\d+(?:\.\d+)?"

_NUMBER_TOKEN_RE = re.compile(
    "|".join([_TR_GROUPED_RE, _US_GROUPED_RE, _TR_DECIMAL_RE, _PLAIN_RE])
)

_SUFFIX_RE = re.compile(r"\s*(%|milyar|milyon|bin|x\b|kat\b)", re.IGNORECASE)

_SCALE_WORDS = {"milyar": 1_000_000_000.0, "milyon": 1_000_000.0, "bin": 1_000.0}


def _looks_grouped(parts: list[str]) -> bool:
    # A single "123.456"-shaped group is genuinely ambiguous (US thousands
    # grouping of an under-1000 number, vs. a 3-decimal-place fraction) —
    # except when the leading part is "0" (or "-0"), since nobody writes
    # "0,264" or "0.264" to mean the integer 264. That leaves the decimal
    # reading as the only sensible one for a leading zero.
    if len(parts) > 2:
        return True
    return len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3 and parts[0] not in ("0", "-0")


def _parse_number_literal(token: str) -> float | None:
    has_dot = "." in token
    has_comma = "," in token
    try:
        if has_dot and has_comma:
            # Whichever separator appears last is the decimal point.
            if token.rfind(",") > token.rfind("."):
                return float(token.replace(".", "").replace(",", "."))
            return float(token.replace(",", ""))
        if has_comma:
            parts = token.split(",")
            if _looks_grouped(parts):
                return float(token.replace(",", ""))
            return float(token.replace(",", "."))
        if has_dot:
            parts = token.split(".")
            if _looks_grouped(parts):
                return float(token.replace(".", ""))
            return float(token)
        return float(token)
    except ValueError:
        return None


def extract_number_candidates(text: str) -> list[tuple[str, list[float]]]:
    """Finds every numeric token in `text` and, for each, returns the list
    of plausible canonical float values it could represent (more than one
    when a "%" suffix makes the scale ambiguous between a 0-1 ratio field
    and an already-percent-scale field like the TCMB policy rate).

    Returns (matched_span, candidate_values) pairs so callers can report
    which literal text was flagged.
    """
    results: list[tuple[str, list[float]]] = []
    for match in _NUMBER_TOKEN_RE.finditer(text):
        literal = match.group(0)
        value = _parse_number_literal(literal)
        if value is None:
            continue

        # Turkish convention (and format_ratio_percent/format_percent_points)
        # puts "%" — and the sign, for a negative value — BEFORE the digits
        # ("%82,6", "-%5,9"), not after, so neither is part of the regex
        # match above; check the two characters immediately preceding it.
        before = text[max(0, match.start() - 2) : match.start()]
        is_percent = before.endswith("%")
        if before == "-%" and not literal.startswith("-"):
            value = -value

        tail = text[match.end() : match.end() + 12]
        suffix_match = _SUFFIX_RE.match(tail)
        suffix = suffix_match.group(1).lower() if suffix_match else None
        if suffix == "%":
            is_percent = True

        if is_percent:
            candidates = [value / 100, value]
        elif suffix in _SCALE_WORDS:
            candidates = [value * _SCALE_WORDS[suffix]]
        else:
            candidates = [value]

        results.append((literal, candidates))
    return results
