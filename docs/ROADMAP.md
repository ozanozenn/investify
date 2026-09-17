# Roadmap

Full product vision: `MAIN_ROADMAP.md` (repo root). This document tracks
phase-level status. Phase boundaries follow the roadmap's own "57.
GELİŞTİRME STRATEJİSİ" / "PHASE 1" addendum.

## Phase 1 — MVP Vertical Slice — ✅ DONE (this delivery)

Ticker search → real company/financial/KAP/macro data → deterministic
metrics/valuation/scoring → structured LLM interpretation → persisted,
versioned analysis snapshot → Company Detail UI. Full scope boundary and
Definition of Done: [docs/PHASE_1_SCOPE.md](PHASE_1_SCOPE.md).

## Phase 2 — Deepen valuation & history — ✅ DONE

- DCF engine (Bear/Base/Bull scenarios, WACC × terminal-growth sensitivity
  matrix, user-overridable assumptions) — `app/valuation_engine/dcf.py`.
- Historical analysis comparison ("Since previous analysis") —
  `app/services/snapshot_diff.py`, no schema change (ADR-005 held).
- Peer comparison (sector/industry median) — `app/services/peer_comparison.py`;
  required fixing a real sector/industry taxonomy mismatch between the
  curated seed and live yfinance bootstraps (`providers/company/taxonomy.py`).
- Thesis tracking (STRENGTHENED/WEAKENED/UNCHANGED verdict), same service.
- Also delivered alongside Phase 2: Google Gemini as a free-tier LLM
  provider (`llm/gemini_provider.py`), a live TCMB EVDS2→EVDS3 migration
  fix (`providers/macro/evds_client.py`), and a **full Turkish
  localization pass** — UI, LLM output (`company-analysis-v2.md`), error
  messages, and config-driven labels. All future features ship in Turkish
  from the first draft (no English-then-translate).

## Phase 3 — Sector-specific engines (deferred — user decision 2026-09-17)

Explicitly skipped for now: the user wants to keep the system's
technical-metric surface minimal at its current scope and revisit
whether more sector-specific metrics are worth the added complexity
later, rather than build it speculatively now.

- Bank-specific financial engine (NIM, loan/deposit growth, NPL, CAR,
  cost/income) — currently explicitly refused with an "unsupported"
  state (`financial_engine/industry_strategy.py`) rather than a wrong
  generic score. Given how much of BIST's market cap is banks, this
  would likely be the highest-value item if/when this phase is revisited.
- REIT/GYO (NAV, NAV discount, occupancy) and Holding (SOTP, holding
  discount) engines.

## Phase 4 — News, watchlist, alerts (in progress — news done)

- ✅ **News aggregation** — `app/providers/news/google_news_provider.py`
  (Google News RSS search, no API key), title-similarity dedup. No
  clustering or sentiment scoring in this pass (user decision 2026-09-17:
  minimal first, add later if wanted); stateless endpoint
  (`GET /api/companies/{ticker}/news`), not persisted, not wired into the
  LLM context — independent of the financial-analysis pipeline.
- Watchlist — not started (user decision 2026-09-17: deferred, not
  requested yet).
- Alert engine (score change, new important KAP, valuation threshold) —
  not started (user decision 2026-09-17: "anlık bildirim" explicitly
  deferred, not needed right now).
- Context-aware AI chat per company (RAG or structured-context-only,
  per roadmap section 83 — must not answer from uncontrolled internet
  knowledge) — not started.

## Phase 5+ — Advanced

Consensus analyst data (if a legally usable source is found), management
guidance vs. actual tracking, capital allocation engine, accounting
anomaly detection beyond the current absence, full Turkey macro dashboard,
technical analysis indicator set, analysis outcome tracking (not
backtesting — roadmap section 44 is explicit this is not a trading bot).

## Explicit non-goals (forever)

BUY/SELL/HOLD signals, portfolio management, broker integration,
automatic trading. See `MAIN_ROADMAP.md` section 1.
