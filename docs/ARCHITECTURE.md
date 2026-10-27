# Architecture

## System shape

Modular monolith, two deployable apps, per [ADR-001](adr/ADR-001-monorepo-and-backend-framework.md):

```
apps/api   FastAPI + SQLAlchemy(async) + Alembic + Postgres, single Python service
apps/web   Next.js (App Router) + TypeScript + Tailwind, calls apps/api over HTTP
```

Redis is used only as a light cache: today it holds the live quote shown on
page open (`GET /api/companies/{ticker}/quote`, `services/cache.py`, TTL
`QUOTE_CACHE_TTL_SECONDS`, default 60 s). If Redis is unreachable the API
logs one warning and runs without a cache — no request fails because of it.
No Celery in Phase 1: the only
background-shaped operation is the refresh pipeline, and it runs
synchronously inside the request handler for `POST
/companies/{ticker}/refresh` because Phase 1 is single-user and a full
refresh (a handful of HTTP calls) completes in low single-digit seconds.
Introducing Celery/Celery Beat before there is a real concurrency or
scheduling need would violate the "don't overengineer" instruction (roadmap
section 5 of the Phase 1 addendum). The `services/refresh_pipeline.py` stage
interface is written so it can be lifted into a Celery task later without
changing its internals (see `docs/ROADMAP.md` Phase 2 notes).

The one scheduled job (ADR-013) still avoids Celery: a small asyncio loop
(`services/watchlist_scheduler.py`), started from the FastAPI lifespan
(`app/lifespan.py`), runs `services/watchlist_refresh.py` on weekdays after
BIST close — every watchlist ticker sequentially through `run_refresh`, each
with its own `AsyncSession`. `POST /api/watchlist/refresh` starts the same
job in the background. Duplicate runs across uvicorn workers are prevented
by a Postgres advisory lock plus a per-slot "already refreshed" skip.

## Refresh pipeline (implemented)

```
ticker
  -> resolve Company (DB, or bootstrap from static seed list if unknown)
  -> MarketDataProvider.get_quote / get_historical_prices        [SUCCESS/FAILED, observable]
  -> FinancialDataProvider.get_financial_statements               [SUCCESS/FAILED]
  -> DisclosureProvider.get_disclosures                           [SUCCESS/FAILED]
  -> MacroDataProvider.get_series (policy rate, CPI, USD/TRY, EUR/TRY)  [SUCCESS/FAILED, per-series]
  -> normalize financial statements to canonical fields, persist
  -> financial_engine.compute(...)                                 -> FinancialMetricSnapshot
  -> valuation_engine.compute(...)                                 -> ValuationSnapshot
  -> scoring_engine.compute(...)                                   -> ScoreSnapshot
  -> data_quality.compute(...)                                     -> DataQuality
  -> context_builder.build(...)                                    -> StructuredAnalysisContext
  -> llm_provider.analyze(context)                                 -> LLMAnalysisResult (validated)
  -> persist AnalysisSnapshot (immutable)
  -> API response
```

Each stage's outcome (`SUCCESS`/`FAILED`/reason) is recorded in
`DataFetchLog` and surfaced in the API response's `sources`/`freshness`
blocks — this is what section 36 ("Her stage observable olmalı") and
section 37 (partial failure handling) require. A stage failing never raises
past the pipeline boundary; it degrades the result and is shown to the user
as `"X data unavailable"`.

## Phase 2-4 additions (structural summary — see `docs/ROADMAP.md` for full detail)

The pipeline shape above hasn't changed; these are new branches off it:

- **Valuation**: `valuation_engine/dcf.py` adds a DCF engine (Bear/Base/Bull
  scenarios, WACC × terminal-growth sensitivity) alongside the original
  relative valuation, attached to `ValuationMetrics.dcf`.
- **Comparison services**: `services/peer_comparison.py` (sector/industry
  median comparison) and `services/snapshot_diff.py` (comparison against
  the previous `AnalysisSnapshot`, thesis-strength verdict) — both read
  existing persisted data, no new provider stages, no schema change
  (ADR-005 held).
- **LLM**: `llm/gemini_provider.py` added as a second real provider
  (ADR-008). `llm/number_format.py` + `llm/context_formatter.py` sit
  between `context_builder` and the provider call — they turn the raw
  `StructuredAnalysisContext` into the human-formatted JSON the prompt
  actually embeds (see `docs/LLM.md`); `hallucination_guard.py` verifies
  against that same formatting.
- **Market-wide feeds** (`api/routers/market.py`, `api/routers/calendar.py`):
  unlike every router above, these are **not** per-ticker and don't touch
  `AnalysisSnapshot` at all — they query `GoogleNewsProvider`/
  `KapDisclosureProvider`'s market-wide methods directly and are stateless
  (ADR-009). `next_rate_decision_date` is the one piece of calendar data
  that *does* feed into a company's own `StructuredAnalysisContext`.
- **Verdict** (ADR-011): `verdict_engine/engine.py` combines the valuation,
  score and data quality (plus peer medians from
  `services/peer_comparison.py:peer_medians_for_company`) into the
  "Hüküm" card — Ucuz/Makul/Pahalı, Güçlü/Orta/Zayıf, confidence and a
  demo AL/TUT/SAT signal. Computed during refresh, stored in the
  snapshot's `context_json.verdict`; not yet part of the LLM prompt.

## Import direction (enforced by convention, see ADR-001)

```
api/routers -> services -> {providers, financial_engine, scoring_engine, valuation_engine, verdict_engine, llm} -> models
```

`financial_engine`, `scoring_engine`, `valuation_engine`, `verdict_engine` are pure: typed
input in, typed (`score`, `contribution`, `reason`) output out, no I/O. This
is what makes them independently unit-testable against fixtures (section 49)
and is the mechanism behind the "LLM never computes" rule (ADR-003).

## Request-time vs refresh-time (section 85: performance)

`GET /companies/{ticker}/analysis` never calls a provider — it only reads
the latest persisted `AnalysisSnapshot` (+ latest cached market snapshot for
price/market-cap freshness). Only `POST /companies/{ticker}/refresh` talks
to providers/LLM. First-time ticker lookup triggers one implicit refresh so
the demo flow ("type THYAO, get a full screen") works without a separate
manual step. The one exception is `GET /companies/{ticker}/quote`: it calls
only `MarketDataProvider.get_quote` (Redis-cached, never creates a
snapshot) so the header price is fresh on page open; if the provider fails
it returns the latest snapshot's price marked `stale: true`.

## Frontend information architecture

Single Company Detail screen for Phase 1 (`docs/PHASE_1_SCOPE.md`), backed
entirely by `GET /api/companies/{ticker}/analysis`. No client-side financial
computation — every number rendered comes from the API response verbatim
(section 59: "frontend'de finansal hesaplama" is forbidden).

## Cross-cutting

- **Config**: `pydantic-settings`, env-driven, `config/*.yaml` for
  non-secret tunables (analysis horizons, scoring weights) per roadmap
  section 54 — see `apps/api/app/core/config.py` and
  `apps/api/config/scoring.yaml`.
- **Logging**: structured JSON logs with `request_id`, `provider`,
  `ticker`, `operation`, `latency_ms`, `result` (section 47).
- **Timezone**: DB stores UTC; API/UI render `Europe/Istanbul` (section 87).
- **Auth**: single-user JWT with a local-dev bypass flag (section 45) — see
  `docs/SECURITY.md`.
