# ADR-006: Python version and local development environment

## Status
Accepted (Phase 1)

## Context
[ADR-001](ADR-001-monorepo-and-backend-framework.md) already states "Python
3.12 in Docker; a 3.11 local venv is acceptable for development... since no
Phase 1 dependency requires 3.12-only features" and forward-references this
ADR for the detail — this document fills that gap.

A real incident drove the decision to make the 3.11-local/3.12-Docker split
explicit rather than just asserting "use 3.12 everywhere": a development
machine had no working Python or Docker at session start. The system
`python3` was broken via a stale Xcode Command Line Tools shim (not a
project problem — an environment problem), and Docker wasn't installed at
all. Getting a working local loop required installing Python 3.11 via
Homebrew and creating a fresh `apps/api/.venv`, rather than matching the
Docker image's 3.12 exactly.

While building that local environment, a missing `greenlet` pin (required
by SQLAlchemy's async engine) was found — apparently present transitively
via some other package on the original Linux dev machine, but not
guaranteed, so it needed to be an explicit dependency.

## Decision
- **Docker images**: Python 3.12-slim (`apps/api/Dockerfile`,
  `FROM python:3.12-slim`). This is the version of record — CI/deploy
  should always match this.
- **Local development venv**: Python 3.11 is explicitly acceptable. Nothing
  in Phase 1-4's dependency set requires a 3.12-only language feature, so
  pinning local dev to exactly match Docker is not worth the friction of
  requiring a specific Python installed on every contributor's machine.
- `greenlet>=3.0,<4` is an explicit dependency in `apps/api/pyproject.toml`
  (not relied upon transitively) because SQLAlchemy's async engine needs it
  and its presence isn't guaranteed by any other direct dependency.
- When Docker is unavailable, backend verification may fall back to SQLite
  instead of the Postgres container — acceptable for unit/engine-level
  tests (no Postgres-specific SQL used in Phase 1-4), but integration tests
  that depend on Postgres-specific behavior should still be run against the
  real `docker compose` stack before considering a change done.

## Consequences
- A contributor (or agent) with only Python 3.11 available locally can
  still develop and run the full test suite without Docker.
- Docker remains the source of truth for "does this actually work in the
  real deployment target" — local-venv-only verification is not a
  substitute for at least one `docker compose up -d --build` pass before
  shipping a change that touches dependencies, migrations, or anything
  environment-sensitive.
- If a future dependency genuinely requires a 3.12-only feature, this ADR
  should be revisited (status → Superseded) rather than silently making the
  local venv unusable.
