# ADR-001: Monorepo layout and backend framework

## Status
Accepted (Phase 1)

## Context
MAIN_ROADMAP.md proposes a `packages/*` split (financial-engine, scoring-engine,
valuation-engine, data-providers, llm, shared) as separate installable packages.
It also explicitly asks to avoid overengineering for a single-user MVP and to
prefer a **modular monolith** (section "5. OVERENGINEERING YAPMA").

Splitting Python code into separately-versioned packages this early adds
packaging overhead (workspace tooling, inter-package versioning, editable
installs) with no present benefit — there is exactly one consumer (the API
process) and one contributor (this project).

## Decision
Use a two-app monorepo:

```
apps/
  api/     FastAPI backend (single Python package, internally modular)
  web/     Next.js frontend
docs/
scripts/
infrastructure/
```

Inside `apps/api/app/`, keep strict module boundaries that mirror the
roadmap's intended package split, so extracting any of them into a real
package later is a mechanical move, not a redesign:

```
app/
  core/              settings, logging, db session
  models/            SQLAlchemy ORM models (domain)
  schemas/           Pydantic request/response + context schemas
  providers/         provider ABCs + implementations (market/financial/disclosure/macro)
  financial_engine/  deterministic metric calculations
  scoring_engine/    deterministic scoring
  valuation_engine/  deterministic relative valuation (+ DCF slot for later)
  llm/               LLMProvider abstraction, OpenAI impl, mock impl, prompts
  services/          orchestration: refresh pipeline, structured context builder
  api/routers/       FastAPI routers (HTTP layer only, no business logic)
  db/                Alembic environment + migrations
```

Rule enforced by convention (checked in review, not tooling, for Phase 1):
`api/routers` may import from `services`, `schemas`; `services` may import
`providers`, `financial_engine`, `scoring_engine`, `valuation_engine`, `llm`,
`models`; the engines (`financial_engine`, `scoring_engine`, `valuation_engine`)
must never import `providers` or `llm` — they are pure functions over typed
inputs. `llm` must never import `models` (no ORM/DB access from the LLM layer),
only `schemas`.

Backend framework: **FastAPI + Pydantic v2 + SQLAlchemy 2.x (async) + Alembic**,
as specified in the roadmap. Python 3.12 in Docker; a 3.11 local venv is
acceptable for development (see ADR-006 note) since no Phase 1 dependency
requires 3.12-only features.

## Consequences
- Extracting `packages/financial-engine` etc. later (e.g. if a second
  consumer — a CLI, a worker — needs it) is a `git mv` + `pyproject.toml`
  split, not a rewrite, because the module already has no upward imports.
- We lose independent versioning of engines in Phase 1. Acceptable: the
  roadmap already tracks engine versions as strings in
  `analysis_snapshots` (financial_engine_version, scoring_version, ...),
  which does not require separate packages.
