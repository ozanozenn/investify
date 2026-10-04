# ADR-010: Test strategy and repo structure

## Status
Accepted (Phase 4 — re-affirms ADR-001, backend test approach already in
practice; frontend test approach decided here, not yet implemented)

## Context
Two related questions came up while setting up this project's agent-based
workflow: whether the monorepo layout from ADR-001 still holds now that the
frontend needs a real automated test suite (it currently has none beyond
`typecheck`/`lint`/`build`), and what that test suite should actually be.

## Decision

### Repo structure: stays a monorepo
ADR-001's reasoning (avoid packaging/workspace overhead for a single
contributor, single consumer) still applies — nothing about adding frontend
tests requires splitting `apps/api` and `apps/web` into separate
repositories. Fully independent test suites, configs, and even CI jobs are
achievable within the current `apps/*` layout. Revisit only if a concrete,
specific need appears (e.g. independent deploy cadences, a second team) —
not speculatively.

### Backend tests (already in practice, documented here for the first time)
`pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`), `tests/unit/` for
pure functions/engines and provider tests (HTTP mocked with `respx`),
`tests/integration/` for API-endpoint-level tests against a real test
client. `ruff` for lint (`line-length = 100`). Run via
`.venv/bin/pytest tests/ -q` / `.venv/bin/ruff check .`.

### Frontend tests: none yet — Vitest + React Testing Library planned
`apps/web/package.json` has no `test` script and no test framework
dependency today — `typecheck`, `lint`, and `build` are the only automated
checks, backed up by manual, uncommitted live-verification (Playwright
scripts run ad hoc each session, screenshots checked by hand, not a
regression suite). Decision for when this is built: **Vitest + React
Testing Library** for unit/component tests (fits Next.js 15 / React 19 /
ESM better than Jest, fast, no separate transform config needed). The
existing ad hoc Playwright live-verification pattern is a candidate to
formalize into a committed E2E suite later, but that's a separate decision
from unit/component testing. **Not implemented as part of this ADR** —
tracked as a backlog item in `docs/TECHNICAL_DEBT.md`.

### Deliberately deferred — 2026-10-05
Setup was scoped, planned, and then **consciously not built**. Reasoning,
recorded so it isn't re-litigated: every real defect found across this
project's development so far has been in the backend (FCF sign flip,
hallucination-guard regex, KAP categorization, EVDS migration, Gemini model
deprecation) — none would have been caught by a frontend unit test. The
frontend is a display layer by design (it performs no financial
calculation; see AGENTS.md), so `typecheck` + `build` plus per-change
browser verification covers its realistic failure modes at far lower cost
than maintaining component tests against a UI that is still changing shape.

**Trigger to revisit**: the frontend starting to *transform* numbers rather
than render them. One instance already exists — `dcf-panel.tsx`'s
percent-to-ratio (`/100`) conversion in its assumptions form. If that kind
of logic accumulates, or a second contributor joins, build the suite.

### Known traps for whoever builds this later
From a full discovery pass (2026-10-05) — do not re-derive these:
- **Mock `global.fetch`, not the `lib/api*.ts` modules.** There are five
  separate copy-pasted `request<T>()` wrappers, each throwing its *own*
  error class; `peer-comparison-panel` and `historical-comparison-panel`
  branch on `error instanceof ApiError` + `.status` (404/409). Module-level
  mocks silently kill those branches.
- **`npm run typecheck` breaks the moment test files land** — `tsconfig.json`'s
  `include` covers `**/*.tsx`, so test globals/matcher types must be added
  in the same change.
- **`theme-provider.tsx` throws under jsdom** — it calls `window.matchMedia`,
  which jsdom does not implement. Needs a stub in test setup.
- **`charts/mini-bar-chart.tsx` needs `lightweight-charts` mocked** (canvas).
  Its empty-data path renders "Veri yok" without touching the chart.
- Each test needs a fresh `QueryClient` with `retry: false` (the production
  client in `components/providers.tsx` uses `retry: 1`, which stalls
  error-state tests), and `next/navigation` hooks (`usePathname`,
  `useRouter`, `useParams`) mocked with real values — two call sites
  dereference them unguarded.
- `tr-TR` `Intl` output (separators, NBSP in currency) is ICU-version
  sensitive — verify actual output empirically before hard-coding assertions.

## Consequences
- `test-runner` (`.claude/agents/test-runner.md`) currently has nothing to
  run on the frontend side besides `typecheck`/`lint`/`build` — this gap
  closes once Vitest is actually installed and example tests exist.
- No change to deployment, CI, or how the two apps are built/shipped —
  this ADR is purely about what gets tested and where, not how the repo is
  laid out (that's unchanged from ADR-001).
