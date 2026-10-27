"""Maps İş Yatırım `MaliTablo` item codes to Investify's canonical fields
(ADR-004 pattern, ADR-015).

Only the XI_29 template (sanayi/ticaret/hizmet şirketleri) is mapped. Banks
(UFRS), insurers/brokers (UFRS_K) and savings-finance companies (XI_29K) use
completely different item-code trees (e.g. total assets is `1BL` in XI_29
but `1Z` in UFRS); for those the provider returns nothing and the composite
provider falls back to the other source instead of guessing a mapping.

Where the item codes come from (live access to isyatirim.com.tr was not
possible while writing this; see ADR-015): they were cross-checked across
several independent open-source clients that recorded real responses —
saidsurucu/borsa-mcp `providers/isyatirim_provider.py` (item prefixes),
Yigtwxx/OracleX `backend/tests/fixtures/isyatirim_thyao_2026Q2.json` and
vedattatli/bistmas-2209a `tests/fixtures/isyatirim_fin/TRKCM_2019.json`
(recorded itemCode/itemDescTr pairs), serefsametumutlu/QuaxisLabs
`src/fetchers/isyatirim.py` (live THYAO/SAHOL/BIMAS discovery notes),
taylanyz/stockalyze and caganco/sentio (live-discovered maps). Every code
below appears with the same Turkish label in at least two of them.
`scripts/verify_isyatirim.py --dump-codes` prints the live labels so the
owner can re-confirm the map in one run.

Item-code prefixes carry meaning: `1*`/`2*` are balance-sheet items (a
period-end snapshot), `3*` income statement and `4*` cash-flow / memo items
— and **`3*`/`4*` values are cumulative year-to-date** (period 6 = first
half, 9 = nine months, 12 = full year). Quarterly values therefore have to
be differenced within the year; see `discrete_quarter_values`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from app.models.enums import CanonicalField

XI29_FINANCIAL_GROUP = "XI_29"

# A period counts as "reported" only if total assets is present and non-zero —
# unpublished future periods come back as null/empty, and no real company
# has zero total assets.
PRESENCE_ITEM_CODE = "1BL"

# canonical -> ordered candidate item codes; the first one present wins.
ITEM_CODE_MAP: dict[CanonicalField, list[str]] = {
    CanonicalField.REVENUE: ["3C"],  # Satış Gelirleri
    CanonicalField.GROSS_PROFIT: ["3D"],  # BRÜT KAR (ZARAR)
    CanonicalField.EBIT: ["3DF"],  # FAALİYET KARI (ZARARI)
    # Ana Ortaklık Payları (parent share, matches Yahoo's "Net Income");
    # DÖNEM KARI (ZARARI) only if the parent-share line is absent.
    CanonicalField.NET_INCOME: ["3Z", "3L"],
    CanonicalField.CASH: ["1AA"],  # Nakit ve Nakit Benzerleri
    CanonicalField.TOTAL_ASSETS: ["1BL"],  # TOPLAM VARLIKLAR
    # Ana Ortaklığa Ait Özkaynaklar (parent, matches Yahoo's "Stockholders
    # Equity" and keeps ROE/PD-DD consistent with the parent-only net
    # income above); Özkaynaklar (incl. minorities) only as a fallback.
    CanonicalField.EQUITY: ["2O", "2N"],
    CanonicalField.OPERATING_CASH_FLOW: ["4C"],  # İşletme Faaliyetlerinden Kaynaklanan Net Nakit
    CanonicalField.CAPEX: ["4CAI"],  # Sabit Sermaye Yatırımları (reported negative = outflow)
}

# canonical -> item codes that must ALL be present; their values are summed.
SUM_MAP: dict[CanonicalField, tuple[str, ...]] = {
    # Kısa vadeli (2AA) + uzun vadeli (2BA) Finansal Borçlar.
    CanonicalField.TOTAL_DEBT: ("2AA", "2BA"),
    # FAVÖK as BIST data vendors define it: Net Faaliyet Kar/Zararı (3H,
    # excludes "diğer faaliyet gelir/giderleri") + Amortisman Giderleri (4B).
    # There is no EBITDA line in MaliTablo; this is a sum of two reported
    # lines, not an estimate, and it is missing if either line is missing.
    CanonicalField.EBITDA: ("3H", "4B"),
}

# Deliberately NOT mapped: FREE_CASH_FLOW. MaliTablo's "Serbest Nakit Akım"
# (4CB) deducts more than capex (THYAO 2026/6: 4C 74,3 mr + 4CAI -43,6 mr
# but 4CB 13,9 mr), so it is a different definition from the engine's
# OCF - |CAPEX| (`financial_engine.formulas.free_cash_flow`). Leaving it out
# lets the engine derive FCF the same way for every source.

# Income-statement / cash-flow fields: cumulative YTD in MaliTablo.
FLOW_FIELDS: frozenset[str] = frozenset(
    {
        CanonicalField.REVENUE.value,
        CanonicalField.GROSS_PROFIT.value,
        CanonicalField.EBITDA.value,
        CanonicalField.EBIT.value,
        CanonicalField.NET_INCOME.value,
        CanonicalField.OPERATING_CASH_FLOW.value,
        CanonicalField.CAPEX.value,
    }
)


@dataclass(frozen=True)
class ResolvedValue:
    value: float
    # Which item code(s) produced the value, e.g. "3Z" or "2AA+2BA". Used so a
    # quarter is only differenced against the previous cumulative period when
    # both came from the same line(s).
    item_codes: str


def parse_item_value(raw: object) -> float | None:
    """MaliTablo values arrive as numeric strings ("2360037000000"), numbers
    or null/"". Anything else (including comma-formatted strings, which are
    ambiguous in Turkish locale) is treated as missing, never guessed."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
    elif isinstance(raw, str):
        text = raw.strip()
        if not text or text.lower() == "null" or "," in text:
            return None
        try:
            value = float(text)
        except ValueError:
            return None
    else:
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def resolve_period(items: Mapping[str, float]) -> dict[str, ResolvedValue]:
    """`items` is {itemCode: value} for ONE period (already parsed, no
    missing values). Returns {canonical field: ResolvedValue}."""
    out: dict[str, ResolvedValue] = {}
    for field, candidates in ITEM_CODE_MAP.items():
        for code in candidates:
            if code in items:
                out[field.value] = ResolvedValue(items[code], code)
                break
    for field, codes in SUM_MAP.items():
        if all(code in items for code in codes):
            out[field.value] = ResolvedValue(sum(items[code] for code in codes), "+".join(codes))
    return out


def discrete_quarter_values(
    current: Mapping[str, ResolvedValue],
    previous: Mapping[str, ResolvedValue] | None,
    fiscal_quarter: int,
) -> dict[str, float]:
    """Single-quarter values for a quarterly `RawFinancialPeriod` (what
    yfinance's quarterly statements contain).

    Balance-sheet fields are snapshots and pass through. Flow fields are
    cumulative YTD: Q1 passes through, Q2..Q4 = this cumulative - previous
    cumulative of the same year. If the previous period (or the same field
    from the same item code in it) is missing, the flow field is left out —
    a cumulative figure is never presented as a single quarter."""
    values: dict[str, float] = {}
    for field, resolved in current.items():
        if field not in FLOW_FIELDS or fiscal_quarter == 1:
            values[field] = resolved.value
            continue
        prior = previous.get(field) if previous else None
        if prior is None or prior.item_codes != resolved.item_codes:
            continue
        values[field] = resolved.value - prior.value
    return values
