# Technical Debt

Explicit shortcuts taken to ship Phase 1, per the instruction to document
these here rather than leave them as scattered `TODO`s. None of these
block the Phase 1 Definition of Done; all are candidates for Phase 2+.

## Valuation

- **Historical multiples assume a constant (current) share count applied
  to historical prices** (`valuation_engine/engine.py` module docstring).
  For a company with material share issuance/buybacks in the lookback
  window, historical P/E, P/B, EV/EBITDA are biased. Flagged per-response
  via `ValuationMetrics.missing_fields` containing
  `"historical_valuation_uses_current_share_count_approximation"`.
  **Fix**: persist `shares_outstanding` per period (from provider, where
  available) instead of only on the latest `MarketSnapshot`.

## Macro data

- **TCMB EVDS series codes are unverified against a live key**
  (`providers/macro/evds_client.py`): `TP.APIFON4` (funding cost, used as
  the policy-rate proxy) and `TP.FG.J0` (CPI index, YoY computed
  client-side) were chosen from public documentation/community usage, not
  confirmed against a real API response, because this environment has no
  `EVDS_API_KEY`. **Fix**: once a key is available, run one real request
  per series and confirm the field name / value shape matches what
  `evds_client.py` expects; adjust if not.

## Search

- `providers/company/ticker_index.py` is a ~60-symbol static index for
  autocomplete only — not the full ~500-company BIST universe. Typing an
  exact ticker outside this list still works (falls through to the DB /
  live `yfinance` bootstrap), but it won't autocomplete. **Fix**: a
  one-time company-list import job (BIST publishes a constituent list) to
  populate `tickers`/`companies` at bootstrap instead of on first search.

## KAP disclosure categorization

- `providers/disclosure/kap_provider.py:categorize()` is simple keyword
  matching against the disclosure subject; most KAP items (observed live
  against THYAO) fall into `OTHER`. Roadmap section 20 envisions LLM-driven
  sentiment/impact/importance classification per disclosure — entirely
  deferred to Phase 2+ (`docs/PHASE_1_SCOPE.md`), this keyword pass is
  just enough to color-code the Phase 1 KAP list, not a real classifier.

## Refresh execution model

- The refresh pipeline runs **synchronously inside the HTTP request
  handler** (no Celery/background queue — see
  `docs/ARCHITECTURE.md` "System shape" for the reasoning: single user,
  a few HTTP calls, low seconds). This will not scale to concurrent
  multi-user refreshes or scheduled/periodic auto-refresh (roadmap section
  53). **Fix**: lift `services/refresh_pipeline.run_refresh` into a Celery
  task (or equivalent) once either need materializes — its signature was
  kept side-effect-isolated (one `AsyncSession`, no global state) for
  exactly this reason.

## Testing

- Integration tests (`apps/api/tests/integration/`) run against an
  **in-memory SQLite** database (via `aiosqlite`), not Postgres, for speed
  and to avoid a hard dependency on Docker being up during `pytest`. The
  ORM models are simple enough that this is safe (JSONB has an explicit
  `.with_variant(JSON(), "sqlite")` fallback; nothing else uses
  Postgres-specific types), but it is not a substitute for occasionally
  running the suite against real Postgres. The manual end-to-end
  verification in this delivery (documented in the final summary) *was*
  run against real Docker Postgres — this note is about the automated
  suite specifically.
- **No automated frontend component tests** (Jest/RTL) were written in
  this Phase 1 delivery, despite roadmap section 49 calling for them. The
  frontend was verified via `next build`'s type-check, plus manual/curl-
  driven verification of the backend it consumes. This is the one
  Definition-of-Done item delivered at reduced rigor — flagged here rather
  than silently claimed as done. **Fix**: add Vitest + React Testing
  Library and at minimum cover the 4 states in `app/company/[ticker]/page.tsx`
  (loading, error, unsupported-industry banner, populated).

## Auth

- Single hardcoded user via env vars, no user table, no password hashing
  library (plain `hmac.compare_digest` string comparison against the env
  value — acceptable only because this is a single local-network personal
  tool with the password itself living in a gitignored `.env`, never in
  code). Do not reuse this pattern if this ever becomes multi-user.
