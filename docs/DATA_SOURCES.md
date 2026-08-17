# Data Sources

Full research and rationale: [ADR-002](adr/ADR-002-data-provider-selection.md).
This document is the operational quick-reference.

| Domain | Phase 1 source | Auth needed | Cost | Notes |
|---|---|---|---|---|
| Market prices (quote, OHLCV) | Yahoo Finance via `yfinance` (`<TICKER>.IS`) | No | Free | Unofficial, rate-limited; soft-fails to `ProviderUnavailableError` |
| Financial statements (Income/Balance/Cash Flow) | Yahoo Finance via `yfinance` | No | Free | Coverage/depth varies by company; normalized via `providers/financial/yfinance_mapping.py` |
| Company disclosures (KAP) | `kap.org.tr` public JSON API | No | Free | Unofficial but publicly served, no auth wall. See endpoints below. |
| FX (USD/TRY, EUR/TRY) | Yahoo Finance (`USDTRY=X`, `EURTRY=X`) | No | Free | |
| Policy rate, CPI | TCMB EVDS (`evds2.tcmb.gov.tr`) | **Yes — free registration** | Free | `EVDS_API_KEY` env var. Falls back to a labeled static seed if unset. |
| LLM interpretation | OpenAI (Structured Outputs) | **Yes — paid** | Pay-per-token | `OPENAI_API_KEY` env var. Falls back to `MockLLMProvider` if unset. |

## KAP endpoints in use (unofficial, verified live 2026-08-17)

```
GET  https://www.kap.org.tr/tr/api/member/filter/{ticker}
     -> resolve ticker to mkkMemberOid + company title

POST https://www.kap.org.tr/tr/api/disclosure/members/byCriteria
     body: {"fromDate": "YYYY-MM-DD", "toDate": "YYYY-MM-DD",
            "mkkMemberOidList": [oid], "subjectList": []}
     -> disclosure list (title, publishDate, disclosureIndex, subject, ...)
```

Required headers: `Content-Type: application/json`,
`Referer: https://www.kap.org.tr/tr/bildirim-sorgu` (list) or
`https://www.kap.org.tr/tr/bildirim-sorgu` (lookup), a real `User-Agent`.
Client enforces a minimum 500ms interval between requests
(`providers/disclosure/kap_client.py: _RATE_LIMIT_SECONDS`).

## Setting up the credentialed sources

1. **TCMB EVDS**: register at https://evds2.tcmb.gov.tr, generate an API key
   from your profile page, put it in `.env` as `EVDS_API_KEY`.
2. **OpenAI**: create an API key at https://platform.openai.com, put it in
   `.env` as `OPENAI_API_KEY`. Optional `OPENAI_MODEL` (default
   `gpt-4.1-mini`).

Without either key the system runs end-to-end with clearly labeled mock data
for exactly those two areas (`is_mock: true` on the affected fields, and a
`[MOCK LLM — no OPENAI_API_KEY set]` prefix on the LLM executive summary).

## Deferred sources (see MAIN_ROADMAP.md, not built in Phase 1)
Consensus analyst data, licensed BIST Data Store feed, general news APIs,
investor-relations RSS. See `docs/PHASE_1_SCOPE.md`.
