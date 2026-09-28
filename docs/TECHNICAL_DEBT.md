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

- **TCMB EVDS series codes are now live-verified against a real key —
  FIXED, and a real platform migration was found and fixed along the
  way.** This item started as "unverified against a live key" in Phase 1;
  a real `EVDS_API_KEY` was added 2026-09-17, and both `TP.APIFON4`
  (policy-rate proxy) and `TP.FG.J0` (CPI index, YoY computed
  client-side) now resolve and parse correctly. Getting there surfaced
  that TCMB has migrated EVDS2 to a new platform ("EVDS3") since Phase 1
  was written, breaking the client in three independent ways — see
  `providers/macro/evds_client.py`'s module docstring for the full
  detail, summarized here:
  1. The endpoint moved (`evds2.tcmb.gov.tr/service/evds` →
     `evds3.tcmb.gov.tr/igmevdsms-dis/`); the old path now serves EVDS3's
     web app HTML rather than a redirect to the new API path.
  2. The API key moved from a `key=` query parameter to an HTTP header.
  3. The server expects `key=value&...` appended directly to the base URL
     with no leading `?` (a literal path suffix, not a standard query
     string) — confirmed against a community client
     ([fatihmete/evds](https://github.com/fatihmete/evds)) that had
     already adapted to this.
  4. Monthly series dates changed format (`"MM-YYYY"` → `"YYYY-M"`,
     not zero-padded).
  Separately (not an EVDS3 change, just a real-world data characteristic):
  **TCMB's CPI index has an observed ~8-month publishing lag** (as of
  2026-09-17, the latest available point was January 2026). The YoY
  computation's fetch window was previously anchored tightly to "today"
  and missed the 12-months-back comparison point once actual data was
  this stale; widened to `_CPI_LOOKBACK_DAYS = 800` days so the window
  reaches far enough back from whatever the *latest published* point
  turns out to be, not from today. If TCMB's lag ever exceeds this, the
  existing `len(rows) < 13` guard still fails safely (falls back to the
  labeled mock) rather than computing a wrong number.
  Live-verified end-to-end via a real `/refresh` call: `policy_rate`,
  `cpi_yoy`, `usdtry`, `eurtry` all returned `is_mock: false` with
  current, correct values.

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

## LLM providers

- **The real prompt-loading path (`OpenAIProvider`/now also
  `GeminiProvider`) was silently broken since Phase 1 — FIXED.**
  `Settings.llm_prompt_version` defaults to `"company-analysis-v1"`
  (hyphenated) and `docs/LLM.md` documented that exact filename, but the
  actual file on disk was `llm/prompts/company_analysis_v1.md`
  (underscored) — `load_prompt_template()` would have raised
  `LLMProviderError: unknown prompt version company-analysis-v1` on the
  very first real (non-mock) refresh. This was never caught because no
  environment this project has run in ever had a real `OPENAI_API_KEY`
  configured — `MockLLMProvider` never touches the prompt file, so the
  mismatch had zero real-world coverage until writing `GeminiProvider`'s
  tests exercised the loader for the first time. **Fix**: renamed the file
  to `llm/prompts/company-analysis-v1.md` to match the documented/coded
  default (not the other way around, since `docs/LLM.md` and
  `Settings.llm_prompt_version` already agreed with each other — only the
  physical filename was the outlier); updated the one stale reference in
  ADR-003. If you ever add a real `OPENAI_API_KEY`/`GEMINI_API_KEY` for
  the first time, this is exactly the kind of only-hit-by-real-traffic gap
  worth double-checking for elsewhere too.

## Phase 2 additions

- **Sector/industry taxonomy was inconsistent across bootstrap paths,
  silently breaking peer comparison — FIXED.**
  `services/company_bootstrap.py` groups peers by exact string match on
  `Industry.name`/`Sector.name`. The curated `providers/company/seed.py`
  (8 validation tickers) uses hand-picked Turkish labels (e.g. THYAO:
  `sector="Ulaştırma"`, `industry="Havayolu"`); every other ticker
  bootstraps via live `yfinance`'s English GICS-like taxonomy (e.g. PGSUS:
  `sector="Industrials"`, `industry="Airlines"`). Verified live: before the
  fix, THYAO vs PGSUS — two real BIST airlines — produced zero peers
  (`peer_group_basis="none"`) purely because the strings never matched,
  even though `services/peer_comparison.py`'s grouping logic itself was
  already correct (also verified live: SISE `"Sanayi"/"Cam"` vs EREGL
  `"Sanayi"/"Demir Çelik"`, both seeded, correctly fell back to a
  `"Sanayi"` sector match with a real computed median).
  **Fix applied**: `providers/company/taxonomy.py` (new) translates
  yfinance's raw `(sector, industry)` into the seed's canonical Turkish
  taxonomy, keyed primarily by `industry` (more specific than `sector`
  alone). `company_bootstrap.py` now calls
  `normalize_sector_industry(...)` before creating/looking up
  `Sector`/`Industry` rows. Re-verified live post-fix: THYAO and PGSUS now
  both normalize to `("Ulaştırma", "Havayolu")` and correctly peer-match
  (`peer_group_basis="industry"`, PGSUS score 74.9 vs THYAO 56.5).
  **Remaining gap**: the translation table is deliberately not exhaustive
  (same philosophy as `ticker_index.py`) — covers the seed set's own
  industries plus a reasonable set of other common BIST-relevant
  industries (steel, automotive, telecom, banking, refining, food &
  beverage, REIT, mining, utilities, conglomerates/holding). An
  unrecognized yfinance industry string still passes through unchanged
  (never invented), so a newly-bootstrapped company in an uncovered
  industry won't peer-match a seeded company until the table is extended —
  add an entry to `_INDUSTRY_TRANSLATIONS` in `taxonomy.py` as new gaps are
  found, same as extending `ticker_index.py`.
- **DCF bear-case intrinsic value per share can go negative**
  (`valuation_engine/dcf.py`) for companies with material net debt once
  bear-scenario margin/growth deltas push several years of projected FCF
  low enough that `enterprise_value - net_debt` goes negative. Verified
  live against real THYAO data: bear ≈ -1.74 TRY/share vs base ≈ 1.55 vs
  bull ≈ 5.68. This is an arguably-correct reflection of the model under
  stress (a real DCF with enough leverage and pessimistic assumptions can
  imply equity is underwater), not a crash or a `None`, but it was not
  explicitly discussed against the roadmap spec and may read as broken to
  an end user without a UI caveat. **Fix (Phase 2 frontend wave or a
  follow-up)**: decide product-side whether to show a negative per-share
  value as-is (with an explanatory tooltip) or clamp display at 0 with an
  "implies negative equity value under these assumptions" label — a
  numeric/formula bug, not established.
- **This development machine had no working Python/Docker at session
  start** (system `python3` broken via a stale Xcode Command Line Tools
  shim, no `.venv`, no Docker). Python 3.11 was installed via Homebrew and
  a fresh `apps/api/.venv` created; a missing `greenlet` pin (required by
  SQLAlchemy's async engine, apparently present transitively on the
  original Linux dev machine) was found and added to
  `apps/api/pyproject.toml`. Live verification for this phase used SQLite
  instead of Docker Postgres (no Docker available) — the same caveat as
  the existing "Testing" note above, now doubly true until Docker is set
  up on this machine.
- **KAP disclosure categorization (`providers/disclosure/kap_provider.py`)
  was silently inaccurate since Phase 1** — `categorize()` only inspected
  the `subject` field, but KAP frequently sends a generic regulatory
  template name there (e.g. "Özel Durum Açıklaması (Genel)") and puts the
  actual signal ("Pay Geri Alım İşlemleri", "Bedelli Sermaye Artırımı...")
  only in `summary`/title. Found live 2026-09-28 while building the
  market-wide "Haberler"/Takvim feed, where it mattered a lot more (most
  buyback/capital-increase disclosures were silently falling into `OTHER`).
  Fixed by having `categorize()` accept an optional second text argument
  and checking both; both call sites (`kap_provider.py`'s own
  `get_market_disclosures`, and `services/persistence.py`'s per-company
  disclosure save path) now pass it. Also tightened the bare `"sermaye"`
  keyword (false-matched "Sermaye Piyasası Aracı", the generic bond/debt-
  instrument regulatory term, on ordinary coupon-payment disclosures) to
  `"sermaye artır"`/`"sermaye azalt"`/`"bedelli"`/`"bedelsiz"`. The keyword
  list is still best-effort substring matching, not exhaustive — expect to
  keep finding and adding cases the same way.
- **LLM-generated free cash flow figure had a flipped sign, and slipped
  through the hallucination guard undetected — found via an independent
  data-accuracy audit requested by the product owner, 2026-09-28.** A real
  ASELS analysis showed "-10.733.502.000 TL serbest nakit akışı" in a
  thesis-invalidation bullet; the true value (confirmed independently
  against live yfinance data, and self-contradicted by the same report's
  own positive FCF margin figure) was **+10.733.502.000 TL**. Root cause:
  a pure LLM narrative hallucination — the deterministic `FinancialMetrics`
  object held the correct positive value throughout, no engine bug — that
  reached the user because (a) `hallucination_guard.py`'s number regex
  could not parse grouped-thousands numbers as a single token (it split
  "-10.733.502.000" into meaningless fragments), so it never actually
  checked the real value against the context, and (b) even when the guard
  does flag something, `_meta.hallucination_flags` is advisory-only —
  logged, never blocking or triggering a retry. Of 19 other numbers
  independently audited for this same report, 18 reproduced exactly from
  live source data using the app's own formulas — the deterministic
  engines are solid; this was specifically an LLM free-text generation
  failure. Fixed the number-parsing regex (see next item); did **not** add
  blocking/retry-on-hallucination behavior — flags are still advisory-only,
  now at least trustworthy. Consider revisiting whether a non-empty flag
  list should trigger one automatic retry before persisting.
- **Number formatting + prompt rewrite (2026-09-28, product-owner-directed).**
  Numbers embedded in the LLM prompt were raw unrounded floats
  (`0.8259859533087344`), because v1/v2 explicitly forbade the LLM from
  reformatting them (needed for the hallucination guard to verify them
  byte-for-byte). This produced unreadable, stat-dump-style LLM prose,
  flagged directly by the product owner from a real screenshot. Fixed by
  moving formatting into the deterministic layer instead
  (`llm/number_format.py`, `llm/context_formatter.py`): numbers are now
  rendered as human-readable Turkish strings (`%82,6`, `56,7x`,
  `48,9 milyar TL`) before the LLM ever sees them, and the hallucination
  guard's parser was rewritten to undo that formatting when checking LLM
  output instead of expecting plain decimals. New prompt
  `company-analysis-v3.md` was written directly from a 10-question
  conversation with the product owner about desired tone/content — see
  `docs/LLM.md`. A second real regression was found and fixed live while
  verifying this against a real Gemini call: v3's more conversational tone
  led the LLM to spell dates in natural Turkish ("23 Eylül 2026") rather
  than numeric form, which `hallucination_guard.py`'s date-stripping regex
  didn't recognize yet, producing 5 false-positive flags — fixed by
  extending `_DATE_RE`. Known residual limitation: the formatter's
  single-ambiguous-group number parsing (is "5.678" a decimal or the
  integer 5678?) uses a heuristic (leading zero ⇒ decimal, otherwise a
  trailing 3-digit group ⇒ grouped) that isn't 100% unambiguous in theory,
  but the app's own formatter never actually emits the colliding case (it
  only ever produces 1-2 decimal places, never exactly 3), so this has not
  caused a false result in practice.
