# Financial Formula Registry

Implementation: `apps/api/app/financial_engine/formulas.py` (primitives) and
`engine.py` (orchestration). Every formula is unit tested against a
deterministic fixture (`apps/api/tests/fixtures/thyao_like.py`,
`apps/api/tests/unit/test_financial_engine.py`) per roadmap section 49.

All formulas return `None` — never a guessed or zero-substituted value —
when a required input is missing. `FinancialMetrics.missing_fields` lists
which of the 9 core inputs (`Revenue, EBITDA, NetIncome, Equity, TotalDebt,
Cash, TotalAssets, OperatingCashFlow, Capex`) were unavailable for the
latest period, and this feeds `data_quality.completeness`
(`services/data_quality.py`).

## Growth

| Metric | Formula | Edge cases |
|---|---|---|
| Revenue Growth YoY | `(Revenue_t − Revenue_t-1) / \|Revenue_t-1\|` | `None` if no prior period or prior is 0 |
| Revenue CAGR 3Y | `(Revenue_latest / Revenue_earliest)^(1/years) − 1` over up to the last 4 annual points | `None` if either endpoint ≤ 0 (sign change is undefined) or span is 0 years |
| EBITDA Growth YoY | same shape as Revenue Growth YoY, on EBITDA | |
| Net Income Growth YoY | same shape, on Net Income | |
| Growth Consistency | fraction of the last ≤3 YoY revenue growth rates that are positive | `None` if none computable |

## Profitability

| Metric | Formula |
|---|---|
| EBITDA Margin | `EBITDA / Revenue` |
| Net Margin | `NetIncome / Revenue` |
| ROE | `NetIncome / avg(Equity_t, Equity_t-1)` (average equity; falls back to single-period equity if only one period exists) |

## Balance Sheet

| Metric | Formula | Edge cases |
|---|---|---|
| Net Debt | `TotalDebt − Cash` | |
| Net Debt / EBITDA | `NetDebt / EBITDA` | `None` if EBITDA ≤ 0 |
| Debt / Equity | `TotalDebt / Equity` | `None` if Equity ≤ 0 — a negative-equity ratio is not comparable across companies and is suppressed rather than shown |
| Equity / Total Assets | `Equity / TotalAssets` | |

## Cash Flow

| Metric | Formula | Edge cases |
|---|---|---|
| Operating Cash Flow Margin | `OCF / Revenue` | |
| Free Cash Flow | provider's own FCF if present, else `OCF − \|CAPEX\|` | CAPEX sign is normalized to a magnitude subtraction because provider sign conventions vary (Yahoo reports CAPEX negative) |
| FCF Margin | `FCF / Revenue` | |
| FCF Conversion | `FCF / NetIncome` | Only computed when `NetIncome > 0` — conversion off a negative/zero base is not meaningful |

## Explicitly out of Phase 1 scope

Asset Turnover, Inventory Turnover, Receivable/Payable Days, Cash
Conversion Cycle, ROIC, ROA, Interest Coverage, Quick/Current/Cash Ratio —
listed in MAIN_ROADMAP.md section 10 but deferred per
`docs/PHASE_1_SCOPE.md` ("don't inflate scope with dozens of ratios in
Phase 1").

## Sector-specific formulas (banks, REITs, holdings)

Not computed at all in Phase 1 — `financial_engine/industry_strategy.py`
detects `Company.is_financial_industry` and short-circuits the entire
engine/scoring/valuation chain to an explicit "unsupported" state rather
than running the generic industrial formulas against a bank's statements
(which would produce numbers that look plausible but are meaningless — a
bank has no "Revenue"/"EBITDA" line in this sense). See ADR/roadmap section
9 of the Phase 1 addendum ("Yanlış generic skor üretmektense unsupported
state göster").
