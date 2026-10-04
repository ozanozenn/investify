# ADR-002: Phase 1 data provider selection

## Status
Accepted (Phase 1) — Amended by [ADR-009](ADR-009-phase4-data-sources-news-and-calendar.md) (Phase 4: news aggregation, event calendar)

## Context
Section 92/93 of the roadmap require researching current, real options before
picking providers, preferring official APIs, then free reliable providers,
then legally usable public sources, then mock fixtures — and require the
choice to be documented here with the credential situation made explicit.

Research performed 2026-08-17 (web search + live `curl` checks from this
environment):

### Market data & financial statements — `MarketDataProvider`, `FinancialDataProvider`
- **Borsa İstanbul Data Store**: official, licensed, paid, requires a
  commercial account. Not accessible in this environment (no credential).
- **KAP** publishes raw financial statement XBRL/PDF filings but not a
  normalized numeric API for retail use — parsing full XBRL taxonomy per
  company is a multi-week effort by itself, out of scope for Phase 1.
- **Yahoo Finance via `yfinance`**: free, no API key, covers BIST tickers
  under the `<TICKER>.IS` suffix (e.g. `THYAO.IS`), including quotes,
  historical OHLCV, and (with variable depth/history) income statement,
  balance sheet and cash flow statements. Confirmed reachable from this
  environment (`curl` to `query1.finance.yahoo.com` returned HTTP 429 —
  rate-limited, not blocked, i.e. the network path works).
- **Decision: `yfinance` is the Phase 1 `MarketDataProvider` and
  `FinancialDataProvider` implementation.** Known risk: Yahoo applies
  anti-bot rate limiting / occasional IP blocks to unauthenticated
  scraping, and BIST statement coverage/depth varies by company. The
  provider must fail soft (raise a typed `ProviderUnavailableError`) so the
  refresh pipeline marks the stage `FAILED` instead of crashing, per
  section 37 (partial failure handling). No credential required.

### Company disclosures — `DisclosureProvider`
- **KAP (`kap.org.tr`)**: the public site is a Next.js SPA backed by a JSON
  REST API that requires no authentication and is intended for public
  consumption (KAP's own legal mandate is public disclosure). Endpoints
  verified live from this environment:
  - `POST https://www.kap.org.tr/tr/api/disclosure/members/byCriteria`
    — disclosure list by date range + member OID filter.
  - `GET https://www.kap.org.tr/tr/api/member/filter/{ticker}` — resolve
    ticker → `mkkMemberOid` (verified against `THYAO`, returned the correct
    Türk Hava Yolları record).
  - `GET https://www.kap.org.tr/tr/api/notification/attachment-detail/{id}`
    — full disclosure detail (not used in Phase 1; title/date/link is
    enough for the MVP timeline).
- **Decision: real `KapDisclosureProvider` implementation against the
  endpoints above.** This is the same technique used by several public
  open-source KAP tooling projects found during research (KAP_Scraper,
  pykap, kap-notifier). No credential required. Rate-limited client-side
  (min interval between requests) to be a respectful consumer, and the
  provider treats the endpoint as unofficial/unversioned: any non-200 or
  unexpected shape triggers the same soft-fail path as other providers.

### Macro data — `MacroDataProvider`
- **TCMB EVDS (`evds2.tcmb.gov.tr`)**: official Central Bank API, free,
  but registration (email) is required to obtain an API key. **This is a
  credential this environment does not have and the user must obtain.**
  Per section 91/92, this does not block development: the provider is
  implemented for real against the documented EVDS REST contract, reads
  `EVDS_API_KEY` from environment, and if absent falls back to a small,
  explicitly-labeled static seed (`is_mock=True` on every returned
  observation) for `policy_rate` and `cpi_yoy` so the rest of the pipeline
  and UI can be developed/tested end-to-end.
- **USD/TRY, EUR/TRY**: obtainable for free, in real time, with no key via
  `yfinance` (`USDTRY=X`, `EURTRY=X`), so these two series use `yfinance`
  regardless of whether an EVDS key is configured — no reason to mock what
  is already free and real.

### LLM
- **OpenAI**: requires `OPENAI_API_KEY`, a paid account. **Credential not
  available in this environment; the user must supply it.** The
  `LLMProvider` abstraction is implemented for real against the OpenAI
  Responses/Chat Completions API with Structured Outputs
  (`response_format={"type": "json_schema", ...}`), model configurable via
  `OPENAI_MODEL` (default `gpt-4.1-mini` — cheap, supports structured
  outputs, sufficient for Phase 1's single analysis prompt). If
  `OPENAI_API_KEY` is unset, `MockLLMProvider` is used automatically: it
  returns a schema-valid, clearly-labeled placeholder analysis
  (`"executiveSummary"` prefixed with `[MOCK LLM — no OPENAI_API_KEY set]`)
  so the full pipeline runs end-to-end without the key.

## Action required from the user (blocking real data in these two areas only)
1. Register for a free TCMB EVDS account and API key at
   https://evds2.tcmb.gov.tr, set `EVDS_API_KEY` in `.env`.
2. Provide an OpenAI API key with billing enabled, set `OPENAI_API_KEY` in
   `.env`. Optionally set `OPENAI_MODEL`.

Everything else (market data, financial statements, KAP disclosures, FX) uses
real live sources with no credential.

## Consequences
- Phase 1 ships fully functional without either key, in a mode that is
  honestly labeled as partially mocked (`dataQuality` / `is_mock` flags
  flow through to the API response and the UI shows this).
- Swapping any provider later (e.g. moving market data to a licensed BIST
  feed) only touches the corresponding `providers/*` implementation, per
  ADR-001's layering rule.
