# Deployment

## Local development (Docker Compose — recommended)

```bash
cp .env.example .env   # fill in OPENAI_API_KEY / EVDS_API_KEY if you have them
docker compose up --build
```

Brings up `db` (Postgres 16), `redis`, `api` (runs `alembic upgrade head`
then `uvicorn`), `web` (Next.js). API on `:8000`, frontend on `:3000`.

## Local development (without Docker)

```bash
# Backend
cd apps/api
python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"
docker compose up -d db redis   # or point DATABASE_URL at your own Postgres
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload

# Frontend
cd apps/web
npm install
cp .env.local.example .env.local
npm run dev
```

## Production posture (not fully hardened in Phase 1 — see docs/SECURITY.md)

- Set `APP_ENV=production`, `AUTH_DEV_BYPASS=false`, a strong random
  `JWT_SECRET`.
- Put Nginx/Traefik in front (`infrastructure/` is reserved for this —
  empty in Phase 1 per YAGNI, not stubbed with placeholder config).
- Use a managed/backed-up Postgres instance; the `investify_db_data` named
  volume in `docker-compose.yml` is a bare-minimum local dev safeguard,
  not a backup strategy.
- This is a single-user personal tool — it is not designed or reviewed for
  multi-tenant or public internet exposure.

## Estimated monthly cost (roadmap section 94)

| Item | Budget MVP | Recommended | Advanced |
|---|---|---|---|
| VPS (Docker Compose host, 2-4 vCPU/4-8GB) | €5-6 (Hetzner CX22-class) | €12-15 (CX32-class) | €25-40 (dedicated vCPU) |
| Database | included (same VPS, Postgres container) | included | managed Postgres (~€15-25) |
| Redis | included (same VPS, container) | included | managed Redis (~€10) |
| LLM (OpenAI, `gpt-4.1-mini`, on-demand refreshes only, single user) | ~€1-3 | ~€5-10 | ~€15-30 (larger model / higher refresh frequency) |
| Market/Financial data (`yfinance`) | €0 | €0 | licensed BIST Data Store feed (€100s-1000s — enterprise pricing, quote on request) |
| KAP data | €0 (public API) | €0 | €0 |
| TCMB EVDS | €0 (free registration) | €0 | €0 |
| News API | not used in Phase 1 | €0-20 (a free-tier news API) | €50-150 (a paid news API with better coverage) |
| **Total** | **~€6-9/mo** | **~€17-25/mo** | **€200-1000+/mo** (driven entirely by whether a licensed market-data feed is added) |

These are rough, current-as-of-2026-08 estimates for a **single-user**
deployment with on-demand (not continuous/streaming) refreshes — not a
quote. The single biggest lever is whether a licensed BIST market-data
feed is ever added; everything else in this project runs on free tiers by
design (ADR-002).
