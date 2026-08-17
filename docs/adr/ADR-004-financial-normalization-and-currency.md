# ADR-004: Financial statement normalization and currency handling

## Status
Accepted (Phase 1)

## Context
Different providers/periods label the same concept differently ("Revenue" vs
"Net Sales" vs "Hasılat"), and values arrive at different scales (TL vs
thousand TL vs million TL). Section 64/65 of the roadmap require a mapping
layer and explicit `value/currency/scale` handling.

## Decision
1. **Canonical line items.** `financial_engine/canonical_fields.py` defines a
   fixed enum of canonical line items for Phase 1 (Revenue, GrossProfit,
   EBITDA, EBIT, NetIncome, Cash, TotalAssets, TotalDebt, Equity,
   OperatingCashFlow, Capex, FreeCashFlow — matching the roadmap's Phase 1
   minimum field list). Each provider implementation is responsible for
   mapping its raw field names to this enum in its own adapter
   (`providers/financial/yfinance_mapping.py`); nothing downstream ever sees
   a provider-specific field name.
2. **Storage.** `financial_values` stores one row per
   `(financial_period_id, canonical_field, value, currency, scale)`. `scale`
   is an integer power-of-ten multiplier applied to `value` to reach base
   currency units (e.g. `scale=1` for already-in-TL, `scale=1000` for
   thousand-TL). All arithmetic in `financial_engine` operates on the
   scaled (base-unit) value, computed once at read time via a SQLAlchemy
   hybrid property, so a formula can never accidentally mix scales.
3. **Currency.** Phase 1 assumes company financial statements are reported
   in TRY (true for all BIST Phase 1 validation companies). The `currency`
   column exists and is populated so this is not a silent assumption, but
   FX-converted multi-currency statement support is explicitly deferred
   (not needed until a USD-reporting company is onboarded).
4. **Guard rail.** `financial_engine` raises `ScaleMismatchError` if it is
   asked to combine two `FinancialValue` rows with different `currency`
   without an explicit conversion step — there is no implicit coercion.

## Consequences
- Adding a new provider only requires a new mapping file, not changes to
  the engine or schema.
- The "1000 TL vs 1 TL" class of bug (section 65) is structurally
  prevented rather than relying on code review discipline.
