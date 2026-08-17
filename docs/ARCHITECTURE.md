# Architecture

## System shape

Modular monolith, two deployable apps, per [ADR-001](adr/ADR-001-monorepo-and-backend-framework.md):

```
apps/api   FastAPI + SQLAlchemy(async) + Alembic + Postgres, single Python service
apps/web   Next.js (App Router) + TypeScript + Tailwind, calls apps/api over HTTP
```

Redis is used only as a light response/provider cache in Phase 1 (see
`docs/ROADMAP.md` "CACHE" section) — no Celery in Phase 1: the only
background-shaped operation is the refresh pipeline, and it runs
synchronously inside the request handler for `POST
/companies/{ticker}/refresh` because Phase 1 is single-user and a full
refresh (a handful of HTTP calls) completes in low single-digit seconds.
Introducing Celery/Celery Beat before there is a real concurrency or
scheduling need would violate the "don't overengineer" instruction (roadmap
section 5 of the Phase 1 addendum). The `services/refresh_pipeline.py` stage
interface is written so it can be lifted into a Celery task later without
changing its internals (see `docs/ROADMAP.md` Phase 2 notes).

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

## Import direction (enforced by convention, see ADR-001)

```
api/routers -> services -> {providers, financial_engine, scoring_engine, valuation_engine, llm} -> models
```

`financial_engine`, `scoring_engine`, `valuation_engine` are pure: typed
input in, typed (`score`, `contribution`, `reason`) output out, no I/O. This
is what makes them independently unit-testable against fixtures (section 49)
and is the mechanism behind the "LLM never computes" rule (ADR-003).

## Request-time vs refresh-time (section 85: performance)

`GET /companies/{ticker}/analysis` never calls a provider — it only reads
the latest persisted `AnalysisSnapshot` (+ latest cached market snapshot for
price/market-cap freshness). Only `POST /companies/{ticker}/refresh` talks
to providers/LLM. First-time ticker lookup triggers one implicit refresh so
the demo flow ("type THYAO, get a full screen") works without a separate
manual step.

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
