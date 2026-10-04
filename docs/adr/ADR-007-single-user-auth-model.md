# ADR-007: Single-user authentication model

## Status
Accepted (Phase 1)

## Context
Investify is built for one person (the product owner) to use against their
own BIST research. The roadmap (section 45) explicitly scopes auth to
single-user — there is no registration flow, no user management, no
multi-tenant data isolation anywhere in the schema. Building a general
auth/identity system for a single consumer would be pure overengineering
(the same "don't overengineer for Phase 1" principle behind ADR-001's
monorepo choice).

## Decision
- One hardcoded application identity, configured via settings:
  `Settings.app_user_email` / `Settings.app_user_password`
  (`apps/api/app/core/config.py`). No `users` table, no signup endpoint.
- Standard JWT bearer tokens (`python-jose`, `HS256`), issued by
  `POST /api/auth/login` after verifying the single configured
  email/password pair (`core/security.py:verify_credentials`,
  `create_access_token`). `jwt_expire_minutes` defaults to 7 days.
- `require_user` (`core/security.py`) is the single FastAPI dependency every
  protected router uses (`HTTPBearer`, `auto_error=False`, explicit 401 on
  a missing/invalid token).
- **Local-dev bypass**: when `Settings.auth_dev_bypass` is true (default)
  AND `app_env == "development"`, `require_user` returns the configured
  user without checking a token at all. This exists so
  `docker compose up` is immediately usable without a separate login step
  during development — it must never be true in a non-development
  environment.

## Consequences
- Zero user-management surface area to build, test, or secure beyond one
  password check — appropriate for a single consumer, inappropriate the
  moment there's a second real user.
- If Investify ever needs more than one user, this is a real migration (a
  `users` table, per-user data scoping across every model that currently
  has no owner column, a real registration/invite flow) — not a small
  patch. That migration is out of scope until there's an actual second
  user to design for.
- The dev-bypass flag is a deliberate, documented security trade-off
  scoped to local development; any deployment config must confirm
  `app_env != "development"` (or `auth_dev_bypass=false`) before being
  reachable from anywhere but localhost.
