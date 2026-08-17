# Phase 1 Scope

MAIN_ROADMAP.md describes the final product vision. This document is the
authoritative boundary for what is actually implemented in Phase 1, per the
roadmap's own "PHASE 1 — IMPLEMENTATION SCOPE AND EXECUTION RULES" addendum.

## Phase 1 user flow (implemented, real backend, no hardcoded frontend data)

```
Ticker search (THYAO/ASELS/FROTO/TUPRS/GARAN, extensible list)
  -> Company Detail page
     -> header (name, sector, price, market cap, last updated)
     -> data freshness indicators
     -> financial performance (Revenue/EBITDA/NetIncome/FCF, last ~5y)
     -> financial metrics table (growth, margins, ROE, leverage, FCF)
     -> basic valuation (P/E, P/B, EV/EBITDA vs historical)
     -> deterministic scorecard (Growth/Profitability/BalanceSheet/CashFlow/Valuation/Overall)
     -> latest KAP disclosures (real, from kap.org.tr)
     -> macro context (policy rate, CPI, USD/TRY, EUR/TRY)
     -> LLM executive summary + short/medium/long-term outlook + bull/bear/risks/catalysts/what-to-watch
     -> sources panel (source, url, published_at, fetched_at per data point)
```

## In scope (built)
- Monorepo bootstrap, Docker Compose (Postgres, Redis, api, web)
- Company/Sector/Industry/DataSource domain + ticker search
- Provider abstractions: `MarketDataProvider`, `FinancialDataProvider`,
  `DisclosureProvider`, `MacroDataProvider` — one real implementation each
  (see `docs/DATA_SOURCES.md`)
- Financial statement ingestion + canonical normalization (Income/Balance/CashFlow)
- Financial metric engine: growth, margins, ROE, leverage, cash flow metrics
  (exact list in `docs/FINANCIAL_ENGINE.md`)
- Basic relative valuation: P/E, P/B, EV/EBITDA + historical comparison
- KAP disclosure fetch + simple rule-based categorization
- Macro context: policy rate, CPI, USD/TRY, EUR/TRY
- Deterministic, explainable scoring engine (Growth/Profitability/BalanceSheet/CashFlow/Valuation/Overall)
- Structured Analysis Context builder (typed, DB-only, no provider calls)
- LLM integration: one versioned prompt, OpenAI Structured Outputs, Pydantic
  validation, mock fallback, basic hallucination guard
- Source traceability (`source/source_url/published_at/fetched_at`) and data
  freshness surfaced through the API and UI
- Analysis snapshot persistence (immutable, versioned) — foundation for
  Phase 2 history UI, not the UI itself
- Aggregate `GET /api/companies/{ticker}/analysis` + `POST
  /api/companies/{ticker}/refresh`
- Partial-failure pipeline (one provider failing does not fail the request)
- Data quality score (completeness/freshness/warnings)
- Tests: financial engine (fixture-based), scoring engine, provider parsing,
  API integration (with mocked providers), frontend critical states
- Docker Compose single-command bootstrap, README, environment template

## Explicitly deferred to Phase 2+ (see MAIN_ROADMAP.md for full detail)
DCF engine + WACC sensitivity, Bear/Base/Bull intrinsic valuation, peer
comparison, auto peer discovery, sector-specific engines (banks, REIT,
holding, insurance), news aggregation/dedup/sentiment, RAG company chat,
watchlist, alerts (email/Telegram/push), full macro dashboard, technical
analysis indicators beyond nothing (Phase 1 has none), backtesting,
prediction models, accounting-anomaly detection beyond nothing, consensus
data, guidance tracking, capital allocation engine, historical
comparison UI, portfolio/broker features, Kafka/Kubernetes/microservices.

Nothing for these is stubbed out as empty classes or placeholder
endpoints — per the roadmap's explicit instruction, they are simply absent
from the code and only present as backlog items below.

## Non-goals forever (per MAIN_ROADMAP.md section 1)
BUY/SELL/HOLD signals. This system produces evidence and structured
context, never a trading signal.

## Phase 2 candidate priorities (proposed, not started)
1. DCF engine with Bear/Base/Bull + sensitivity matrix (valuation engine's
   interfaces already leave room for this, see `valuation_engine/base.py`)
2. Peer comparison (sector median already computable from stored data once
   >1 company per sector is ingested)
3. Historical analysis comparison UI (backend already persists the data)
4. Watchlist
5. Bank-specific financial engine (BIST is dominated by a few large banks;
   the current generic engine explicitly refuses to score them — see
   `financial_engine/industry_strategy.py`)
