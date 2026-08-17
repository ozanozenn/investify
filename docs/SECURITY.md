# Security

## Authentication (roadmap section 45)

Single-user JWT auth (`apps/api/app/core/security.py`). There is no user
table — the one account is configured via `APP_USER_EMAIL` /
`APP_USER_PASSWORD` env vars (`.env`, never committed). `POST
/api/auth/login` issues a JWT (HS256, `JWT_SECRET`, 7-day expiry by
default) that must be sent as `Authorization: Bearer <token>` to every
`/api/companies/*` route (wired via `APIRouter(dependencies=[Depends(require_user)])`
in `api/routers/companies.py`).

**Local dev bypass**: when `AUTH_DEV_BYPASS=true` (the `.env.example`
default) *and* `APP_ENV=development`, `require_user` skips token
verification entirely so `docker compose up` is immediately usable without
a login round-trip. Both conditions must hold — flipping `APP_ENV` to
anything else re-enables real auth even with the bypass flag left on,
which is the intended production posture (set `APP_ENV=production` and a
strong `JWT_SECRET` before exposing this beyond localhost).

## Secrets

- `.env` is gitignored; `.env.example` documents every variable with no
  real values.
- `OPENAI_API_KEY` / `EVDS_API_KEY` are read from env only, never logged
  (structured logging in `core/logging.py` logs request metadata, not
  request/response bodies).

## Input validation

All request/response bodies are Pydantic models (FastAPI validates
automatically); the only path parameter is `ticker`, upper-cased and used
solely as a lookup key / external API query parameter — not interpolated
into SQL (SQLAlchemy Core/ORM parameterizes everything) or into a shell
command.

## Rate limiting

Not implemented at the API layer in Phase 1 (single user, not internet-
facing by default). The KAP client self-throttles to ≤2 req/sec as a
considerate-consumer measure (`providers/disclosure/kap_provider.py`),
independent of any inbound rate limit. **Technical debt** — see
`docs/TECHNICAL_DEBT.md` — if this API is ever exposed beyond localhost, add
inbound rate limiting (e.g. `slowapi`) before doing so.

## Dependency vulnerabilities

`apps/web`'s `next` pin was bumped from `15.1.6` to `15.5.23` during
development specifically because `npm install` flagged `15.1.6` as
vulnerable (`CVE-2025-66478` and related advisories). `npm audit` still
reports 5 remaining advisories (2 low, 3 high) whose only fix is
`next@16.3.1` — a major-version bump not taken in this delivery to avoid
an unreviewed breaking upgrade this late in Phase 1. The high-severity
ones are in `sharp` (libvips CVEs), pulled in transitively for Next's
`next/image` optimization pipeline, which this app does not use (no
`<Image>` with remote/untrusted sources — Phase 1 has no images at all).
Practical exposure is therefore low for a localhost single-user app, but
this is real, tracked debt: re-run `npm audit`, evaluate the Next 16
upgrade, and take it in Phase 2 rather than deferring indefinitely.
