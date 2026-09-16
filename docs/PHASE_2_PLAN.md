# Phase 2 Plan — Deepen valuation & history

Status board for Phase 2 (see `docs/ROADMAP.md` for the phase-level one-liner
and `MAIN_ROADMAP.md` sections 13 (DCF), 25 (Thesis Tracking), 26 (Change
Detection) for the full spec this implements against).

Orchestration model: independent backend engines/services are built by
separate agents in isolated git worktrees, each owning **only new files**
(own router file, own service/engine module, own schema module, own config,
own tests) so they can run in parallel with zero merge conflicts. A single
integrator pass (not delegated) wires the new routers into `main.py` and
attaches `dcf` to the default analysis response. Frontend work is a later
wave, sequenced after backend contracts are verified against real data
(same discipline as Phase 1 — no feature is "done" without a live-data
check).

## Wave 1 — Backend engines/services (parallel, worktree-isolated)

| # | Task | Owner | New files only | Status |
|---|------|-------|-----------------|--------|
| 1 | **DCF Engine** — Bear/Base/Bull scenarios, WACC×terminal-growth sensitivity matrix, user-overridable assumptions (roadmap §13) | Agent A | `app/valuation_engine/dcf.py`, `app/schemas/dcf.py`, `app/api/routers/dcf.py`, `config/dcf.yaml`, `tests/unit/test_dcf_engine.py` | dispatched (worktree agent) |
| 2 | **Peer Comparison** — sector/industry median vs this company, explicit "insufficient peers" state when <1 peer refreshed | Agent B | `app/services/peer_comparison.py`, `app/schemas/peer.py`, `app/api/routers/peers.py`, `tests/unit/test_peer_comparison.py` | ✅ landed — 34/34 tests pass, router not yet registered (Wave 2) |
| 3 | **Snapshot Diff + Thesis Tracking** — "Since previous analysis" metric deltas, notable-change filter (roadmap §26), rule-based Thesis Strength verdict (roadmap §25) | Agent C | `app/services/snapshot_diff.py`, `app/schemas/diff.py`, `app/api/routers/comparisons.py`, `config/thesis.yaml`, `tests/unit/test_snapshot_diff.py` | dispatched (worktree agent) |

Dispatched: 2026-09-16. Each agent works in its own isolated git worktree
branched from `development`, creating only new files (no shared-file
edits), so all three can land without merge conflicts. Environment note:
this machine had no working Python/venv/Docker — Python 3.11 was installed
via Homebrew and each worktree creates its own `apps/api/.venv`. A missing
`greenlet` pin (needed by SQLAlchemy's async engine, previously unnoticed
because the original dev machine had it transitively) was found and fixed
in `apps/api/pyproject.toml` — full 29-test Phase 1 suite passes locally
with this fix.

Hard constraint given to all three agents: **no edits to any existing
file** (no `main.py`, no `refresh_pipeline.py`, no `companies.py`, no
`schemas/valuation.py`) — that's the integrator's job, to keep the three
branches conflict-free. Each engine/service must follow the existing
codebase convention: pure functions, `None`/explicit "insufficient/missing"
states instead of guessing, `missing_fields`-style honesty, config-driven
thresholds (no magic numbers), and tests mirroring
`tests/unit/test_valuation_engine.py` style.

## Wave 2 — Integration (not delegated) — ✅ DONE

- Registered `dcf`, `peers`, `comparisons` routers in `app/main.py`. No
  route collisions (`/api/companies/{ticker}/analysis/{dcf,peers,compare}`
  alongside the existing `/analysis`, `/analysis/history`, `/refresh`).
- Added `dcf: DcfResult | None` to `ValuationMetrics` and wired
  `compute_dcf` into `refresh_pipeline.py` — base-case DCF now ships with
  every refresh; the dedicated `dcf` router additionally supports
  on-demand recompute with overridden assumptions without a full refresh.
- Full suite: **46/46 tests pass** (29 Phase 1 + 5 peer + 6 diff + 6 dcf).
- **Live verification against real data** (THYAO/PGSUS/SISE/EREGL via real
  yfinance + KAP, mock LLM, SQLite instead of Docker Postgres — see
  `docs/TECHNICAL_DEBT.md` "Phase 2 additions" for the environment note):
  - DCF: real THYAO run produced bear/base/bull = -1.74 / 1.55 / 5.68
    TRY/share, a 7×7 sensitivity matrix, honest `missing_fields` for
    config-defaulted assumptions. **Finding**: bear can go negative for
    leveraged companies — flagged in TECHNICAL_DEBT.md as a product
    decision, not a bug.
  - Snapshot diff: two back-to-back real THYAO refreshes correctly
    produced an `UNCHANGED` verdict with all-zero deltas (nothing changed
    in the underlying data in that window) — confirms the extraction/diff
    path works against real snapshot shapes without crashing.
  - Peer comparison: **found and fixed a real cross-cutting Phase 1 gap**
    — THYAO (curated Turkish seed labels) vs PGSUS (live yfinance English
    labels) didn't match despite being real-world peers, because
    `company_bootstrap.py` grouped by exact sector/industry string. Added
    `providers/company/taxonomy.py` to normalize yfinance's taxonomy into
    the seed's Turkish one; re-verified live post-fix: THYAO/PGSUS now
    correctly peer-match (`peer_group_basis="industry"`, THYAO 56.5 vs
    PGSUS 74.9, median 74.9). 52/52 tests pass with the fix (6 new
    taxonomy tests). Full writeup in `docs/TECHNICAL_DEBT.md`.
  - Product decision (user, 2026-09-16): DCF's negative bear-case value is
    intentional model output, not a bug — show as-is in the frontend with
    an explanatory note rather than clamping to zero.

## Wave 3 — Frontend — dispatched 2026-09-16

Each as its own new component file (not edits inside the existing
495-line `page.tsx`) to keep this wave parallelizable too; a final
integration pass inserts them into the Company Detail page.

| # | Task | New files only | Status |
|---|------|-----------------|--------|
| 1 | DCF panel: scenario tabs (Bear/Base/Bull), editable assumption overrides, WACC×terminal-growth sensitivity heatmap, honest negative-value note | `lib/api-dcf.ts`, `components/dcf-panel.tsx` | dispatched (worktree agent) |
| 2 | Historical comparison panel: snapshot picker, "Since previous analysis" delta table, Thesis Strength badge | `lib/api-comparisons.ts`, `components/historical-comparison-panel.tsx` | dispatched (worktree agent) |
| 3 | Peer comparison panel: sector/industry median vs company, honest "not enough peers yet" empty state | `lib/api-peers.ts`, `components/peer-comparison-panel.tsx` | dispatched (worktree agent) |

Same constraint as Wave 1: no edits to `page.tsx`, `lib/api.ts`, or
`lib/types.ts` — each agent verifies with `npm run typecheck` + `npm run
build` only (no live backend in an isolated worktree); the integrator
wires all three into the Company Detail page afterward and runs the real
live-browser verification pass (mirrors Phase 1's Playwright-driven
check).

**Integration + live verification — ✅ DONE (2026-09-16).** All three
panels copied in, wired into `page.tsx` (after the "Valuation" card,
before "Investment Thesis"). `npm run typecheck` and `npm run build` both
clean with all three combined. Live end-to-end check: backend
(`uvicorn`, SQLite dev.db) + frontend (`next dev`) launched together,
real Chrome driven via `playwright-core` against
`/company/THYAO` (seeded with 2 real THYAO refreshes + 1 real PGSUS
refresh) — **zero console errors**, all three panels rendered with real
data:
- DCF: scenario tabs worked, sensitivity matrix showed a real 7×7
  heatmap (green/red tinted, `—` correctly shown for the invalid
  WACC≤terminal-growth cell), negative-value explanatory note displayed
  exactly as the product decision specified.
- Historical comparison: Thesis Strength badge showed "Değişmedi"
  (correct — the two THYAO refreshes used identical underlying data), full
  delta table rendered.
- Peer comparison: "Havayolu içinde 1 şirketle karşılaştırılıyor" —
  the taxonomy fix confirmed working live in the actual UI, not just the
  backend script; THYAO (score 57) vs PGSUS (score 75, median) with real
  P/E/P/B/EV-EBITDA multiples.

Phase 2 (DCF, peer comparison, historical comparison/thesis tracking) is
now feature-complete, tested (52 backend tests), and live-verified
end-to-end. Nothing has been committed yet — all changes are in the
working tree pending the user's go-ahead.

## Explicit non-goals for this phase

Automatic peer discovery, advanced/LLM-narrated thesis tracking, portfolio
management — all forever/later per `MAIN_ROADMAP.md` §3558-3598.
