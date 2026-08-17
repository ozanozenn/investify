# Roadmap

Full product vision: `MAIN_ROADMAP.md` (repo root). This document tracks
phase-level status. Phase boundaries follow the roadmap's own "57.
GELİŞTİRME STRATEJİSİ" / "PHASE 1" addendum.

## Phase 1 — MVP Vertical Slice — ✅ DONE (this delivery)

Ticker search → real company/financial/KAP/macro data → deterministic
metrics/valuation/scoring → structured LLM interpretation → persisted,
versioned analysis snapshot → Company Detail UI. Full scope boundary and
Definition of Done: [docs/PHASE_1_SCOPE.md](PHASE_1_SCOPE.md).

## Phase 2 — Deepen valuation & history (proposed next)

- DCF engine (Bear/Base/Bull scenarios, WACC × terminal-growth sensitivity
  matrix) — `valuation_engine`'s interfaces already leave room for this.
- Historical analysis comparison UI ("August vs November") — backend
  already persists every `AnalysisSnapshot`; this is UI + a diff endpoint.
- Peer comparison (sector median, once more than one company per sector
  has been refreshed).
- Thesis tracking ("Since previous analysis: ...").

## Phase 3 — Sector-specific engines

- Bank-specific financial engine (NIM, loan/deposit growth, NPL, CAR,
  cost/income) — currently explicitly refused with an "unsupported"
  state (`financial_engine/industry_strategy.py`) rather than a wrong
  generic score. Given how much of BIST's market cap is banks, this is
  likely the highest-value Phase 3 item.
- REIT/GYO (NAV, NAV discount, occupancy) and Holding (SOTP, holding
  discount) engines.

## Phase 4 — News, watchlist, alerts

- News aggregation with dedup/clustering/sentiment (KAP disclosures are
  covered in Phase 1; general news is not).
- Watchlist.
- Alert engine (score change, new important KAP, valuation threshold) with
  an abstraction that can later add email/Telegram/push.
- Context-aware AI chat per company (RAG or structured-context-only,
  per roadmap section 83 — must not answer from uncontrolled internet
  knowledge).

## Phase 5+ — Advanced

Consensus analyst data (if a legally usable source is found), management
guidance vs. actual tracking, capital allocation engine, accounting
anomaly detection beyond the current absence, full Turkey macro dashboard,
technical analysis indicator set, analysis outcome tracking (not
backtesting — roadmap section 44 is explicit this is not a trading bot).

## Explicit non-goals (forever)

BUY/SELL/HOLD signals, portfolio management, broker integration,
automatic trading. See `MAIN_ROADMAP.md` section 1.
