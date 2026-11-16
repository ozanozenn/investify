# Database

PostgreSQL 16, SQLAlchemy 2.x (async, `asyncpg`), Alembic migrations.
JSONB used for the four snapshot tables' computed-output blobs (roadmap
section "PostgreSQL JSONB kullan").

Schema is intentionally the Phase 1 minimum per roadmap "6. DATABASE
PRENSİBİ" — not a speculative full model of every roadmap entity.

## Tables

```
sectors, industries          — Company taxonomy (roadmap Company domain)
companies, tickers           — Company + N tickers (Phase 1 uses 1:1, BIST only)
data_sources, data_fetch_logs — Provider registry + per-stage observability (section 36/47)

financial_periods            — One row per (company, period_type, fiscal_year, fiscal_quarter)
financial_values             — One row per (period, canonical_field); scale/currency carried
                                per-row (ADR-004) so arithmetic never silently mixes units

market_snapshots              — Append-only price/market-cap observations
kap_disclosures                — Deduplicated by (company, kap_disclosure_index) — section 86
macro_series, macro_observations — Generic time series storage (policy rate, CPI, FX)

financial_metric_snapshots    — JSONB dump of the latest FinancialMetrics computation
valuation_snapshots           — JSONB dump of the latest ValuationMetrics computation
score_snapshots                — JSONB dump of the latest ScoreResult computation
analysis_snapshots             — THE reproducibility backbone (ADR-005): immutable,
                                  versioned, holds the exact LLM input (context_json)
                                  and output (analysis_json) for one refresh

watchlist_items                — One row per watched ticker (single user, no user column)
                                  + result of the last batch refresh job (ADR-013)
```

## Why JSONB for the *_snapshots tables but normalized rows for financial_values

`financial_values` is normalized (one row per canonical field) because it is
read by the financial_engine formula-by-formula and needs to be queried /
joined / indexed per field. The `*_snapshots` tables are write-once,
read-whole outputs of a deterministic computation — there is no query need
to select "just the ROE" out of a `score_snapshots` row, so a JSONB blob
avoids a combinatorial explosion of narrow tables (Growth Score row,
Profitability Score row, ...) for no read benefit. This can be revisited if
Phase 2's historical comparison UI needs to query across snapshots by
individual metric.

## Idempotency (roadmap section 86)

Every ingestion path (`services/persistence.py`) upserts against the row's
natural unique key instead of blind `INSERT`:
- `financial_periods`: `(company_id, period_type, fiscal_year, fiscal_quarter)`
- `financial_values`: `(financial_period_id, canonical_field)`
- `kap_disclosures`: `(company_id, kap_disclosure_index)`
- `macro_observations`: `(macro_series_id, observation_date)`

Re-running `POST /companies/{ticker}/refresh` never duplicates a row.

## Migrations

```bash
cd apps/api
alembic revision --autogenerate -m "message"
alembic upgrade head
```

The initial migration (`cbb5490621ad_initial_schema.py`) was generated
against a live local Postgres 16 instance and applied successfully during
development (see README "Verified" section).
