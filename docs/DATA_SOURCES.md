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
| LLM interpretation | OpenAI (Structured Outputs) | **Yes — paid** | Pay-per-token | `OPENAI_API_KEY` env var. Takes priority if set. |
| LLM interpretation (dev alternative) | Google Gemini | **Yes — free tier** | Free (rate-limited) | `GEMINI_API_KEY` env var. Used only if `OPENAI_API_KEY` is unset. Falls back to `MockLLMProvider` if neither key is set. |

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
3. **Gemini** (free-tier alternative to OpenAI, good for local dev):
   create an API key at https://aistudio.google.com/apikey, put it in
   `.env` as `GEMINI_API_KEY`. Optional `GEMINI_MODEL` (default
   `gemini-2.0-flash`). Only used if `OPENAI_API_KEY` is unset — see
   `services/provider_bundle.py` for the selection order
   (OpenAI → Gemini → mock). Implemented by `llm/gemini_provider.py`,
   which conforms to the same `LLMProvider` interface as `OpenAIProvider`
   (ADR-003) — every number the model sees still comes only from the
   deterministic `StructuredAnalysisContext`, and its raw JSON response is
   always explicitly Pydantic-validated against `LLMAnalysisResult` before
   being trusted, regardless of provider.

Without a macro/LLM key the system runs end-to-end with clearly labeled
mock data for exactly those two areas (`is_mock: true` on the affected
fields, and a `[MOCK LLM — no OPENAI_API_KEY or GEMINI_API_KEY set]`
prefix on the LLM executive summary).

## Deferred sources (see MAIN_ROADMAP.md, not built in Phase 1)
Consensus analyst data, licensed BIST Data Store feed, general news APIs,
investor-relations RSS. See `docs/PHASE_1_SCOPE.md`.
