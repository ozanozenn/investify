# Investify — BIST Investment Intelligence Platform

A personal, evidence-based investment research platform for Borsa İstanbul
(BIST) companies. **Not a trading bot and never produces a BUY/SELL/HOLD
signal** — it organizes the financial, valuation, KAP, macro and LLM-
interpreted context a careful analyst would want before deciding, so the
user can decide for themself. Full product vision: `MAIN_ROADMAP.md`. This
delivery implements **Phase 1** only — see `docs/PHASE_1_SCOPE.md`.

## What's actually running end-to-end

```
Ticker search (THYAO, ASELS, FROTO, TUPRS, GARAN, or any BIST symbol)
  → real company profile (curated seed or live yfinance bootstrap)
  → real market price/history (Yahoo Finance)
  → real financial statements (Yahoo Finance, canonically normalized)
  → real KAP disclosures (kap.org.tr public JSON API)
  → real FX (Yahoo Finance); policy rate/CPI (TCMB EVDS, or a labeled mock
    seed if you haven't registered a key yet)
  → deterministic financial metrics, valuation, scoring (formula registry:
    docs/FINANCIAL_ENGINE.md / docs/SCORING.md)
  → structured LLM interpretation (OpenAI, or a labeled deterministic mock
    if you haven't set OPENAI_API_KEY yet)
  → persisted, versioned analysis snapshot
  → Company Detail screen
```

This was verified against **real, live data** during development — see
"Verified" below.

## Quick start

```bash
cp .env.example .env
# optional: fill in EVDS_API_KEY / OPENAI_API_KEY — see docs/DATA_SOURCES.md
docker compose up --build
```

- API: http://localhost:8000 (docs at `/docs`)
- Frontend: http://localhost:3000
- Type a ticker (e.g. `THYAO`) into the search box.

Without `docker compose`, see `docs/DEPLOYMENT.md` for running the API and
web app directly.

## Repository layout

```
apps/api/     FastAPI backend — see docs/ARCHITECTURE.md
apps/web/     Next.js frontend
docs/         Architecture, data sources, formula registry, ADRs, roadmap
docker-compose.yml
```

## Documentation map

| Doc | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System shape, refresh pipeline, layering rules |
| [docs/PHASE_1_SCOPE.md](docs/PHASE_1_SCOPE.md) | What's in/out of this delivery, Definition of Done |
| [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) | Every external data source, credential status |
| [docs/DATABASE.md](docs/DATABASE.md) | Schema, idempotency, migrations |
| [docs/FINANCIAL_ENGINE.md](docs/FINANCIAL_ENGINE.md) | Every formula, with edge cases |
| [docs/SCORING.md](docs/SCORING.md) | Scoring model + explainability contract |
| [docs/LLM.md](docs/LLM.md) | Provider abstraction, prompt versioning, hallucination guard |
| [docs/SECURITY.md](docs/SECURITY.md) | Auth model, secrets handling |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Setup, cost estimate |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phase 1 status + proposed Phase 2+ |
| [docs/TECHNICAL_DEBT.md](docs/TECHNICAL_DEBT.md) | Explicit known shortcuts |
| [docs/adr/](docs/adr/) | Architecture Decision Records |

## Tests

```bash
cd apps/api
.venv/bin/pytest tests/ -v
```

29 tests: financial engine (fixture-based, hand-verified expected values),
formula edge cases, scoring engine (interpolation + missing-data rescale),
valuation engine, provider response parsing, and full API integration
tests (mocked providers, real FastAPI app, real deterministic engines, real
mock LLM) covering the happy path, partial-provider-failure, and
first-time-ticker-bootstrap flows.

```bash
cd apps/web
npm run typecheck && npm run build
```

## Verified (this delivery, 2026-08-17)

Ran the live pipeline against real external services from this
environment (not a demo/canned response):
- `POST /api/companies/THYAO/refresh` → real Yahoo Finance price + 4 years
  of financial statements, real KAP disclosures (15 items from
  `kap.org.tr`), real USD/TRY & EUR/TRY, deterministic score 55.7/100 with
  full component breakdown, mock LLM output (no `OPENAI_API_KEY` in this
  environment) with hallucination-guard flags attached.
- `POST /api/companies/GARAN/refresh` (a bank) → correctly returned the
  "unsupported industry" state instead of a misleading generic score.
- `POST /api/companies/SASA/refresh` (a ticker with **no curated seed
  entry**) → correctly bootstrapped a full company profile live from
  Yahoo Finance, proving the general onboarding path (not just the 8
  seeded companies) works.
- `GET /api/companies/THYAO/analysis` on a second call returned the cached
  snapshot with no provider calls (verified via server logs).

## Known gaps in this delivery

See `docs/TECHNICAL_DEBT.md`. The one Definition-of-Done item delivered at
reduced rigor: no automated frontend component tests were written (backend
has 29 passing tests; frontend was verified via TypeScript build +
manual/API-level checks only).
