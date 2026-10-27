# Data Sources

Full research and rationale: [ADR-002](adr/ADR-002-data-provider-selection.md).
This document is the operational quick-reference.

| Domain | Phase 1 source | Auth needed | Cost | Notes |
|---|---|---|---|---|
| Market prices (quote, OHLCV) | Yahoo Finance via `yfinance` (`<TICKER>.IS`) | No | Free | Unofficial, rate-limited; soft-fails to `ProviderUnavailableError` |
| Financial statements (Income/Balance/Cash Flow) | Yahoo Finance via `yfinance` | No | Free | Coverage/depth varies by company; normalized via `providers/financial/yfinance_mapping.py`. Default source. |
| Financial statements — primary candidate ([ADR-015](adr/ADR-015-financial-data-sources-v2.md)) | İş Yatırım `MaliTablo` JSON (KAP-based Turkish statements, XI_29 template) | No | Free (personal use only, see licensing) | **Off by default — not live-verified yet.** Normalized via `providers/financial/isyatirim_mapping.py`. Enable/verify: see below. |
| Company disclosures (KAP) | `kap.org.tr` public JSON API | No | Free | Unofficial but publicly served, no auth wall. See endpoints below. |
| Full BIST company list (search autocomplete) | KAP company-list Excel export + KAP "Sektörler" page | No | Free | Generated offline into `providers/company/bist_companies.json` by `scripts/import_bist_companies.py`; search falls back to the static ~60-ticker index while the file is absent. |
| News | Google News RSS search (`news.google.com/rss/search`) | No | Free | Unofficial but public; live-verified 2026-09-17. Near-duplicate titles merged; not stored, not sent to the LLM ([ADR-009](adr/ADR-009-phase4-data-sources-news-and-calendar.md)). |
| FX (USD/TRY, EUR/TRY) | Yahoo Finance (`USDTRY=X`, `EURTRY=X`) | No | Free | |
| Policy rate, CPI | TCMB EVDS3 (`evds3.tcmb.gov.tr`) | **Yes — free registration** | Free | `EVDS_API_KEY` env var. Falls back to a labeled static seed if unset. Live-verified 2026-09-17 — see `providers/macro/evds_client.py` module docstring for the EVDS2→EVDS3 migration details (new base URL, header-based auth, changed monthly date format). |
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

## İş Yatırım financial statements (ADR-015, not yet live-verified)

```
GET https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo
    ?companyCode=THYAO&exchange=TRY&financialGroup=XI_29
    &year1=2025&period1=3&year2=2025&period2=6&year3=2025&period3=9&year4=2025&period4=12
-> {"ok": true, "value": [{"itemCode": "3C", "itemDescTr": "Satış Gelirleri",
                           "itemDescEng": "Net Sales", "value1": "...", ..., "value4": "..."}]}
```

- Exactly four (year, period) pairs per request; `valueN` = `yearN/periodN`.
  Values are full TRY units as numeric strings (null = not published).
- `3*` (income statement) and `4*` (cash flow) items are cumulative YTD; the
  provider converts quarters to single-quarter values.
- Only the XI_29 (industrial) template is mapped; banks/insurers return an
  empty list there and fall back to the other source.

Settings (`.env`), defaults keep the yfinance-only behaviour:

| Variable | Default | Meaning |
|---|---|---|
| `FINANCIAL_PROVIDER_PRIMARY` | `yfinance` | `yfinance` or `isyatirim` |
| `FINANCIAL_PROVIDER_FALLBACK` | `none` | `none`, `yfinance` or `isyatirim` — used when the primary fails/returns nothing; also the cross-check partner |
| `FINANCIAL_CROSS_CHECK` | `false` | Query both; values differing beyond `config/financial_sources.yaml` tolerance become a Turkish data-quality warning (primary value is kept) |

Verify on a machine with internet access before enabling:

```
cd apps/api
.venv/bin/python scripts/verify_isyatirim.py --dump-codes   # THYAO ASELS FROTO
.venv/bin/python scripts/verify_isyatirim.py SISE BIMAS --quarterly
```

If it passes: `FINANCIAL_PROVIDER_PRIMARY=isyatirim`,
`FINANCIAL_PROVIDER_FALLBACK=yfinance`, `FINANCIAL_CROSS_CHECK=true`.

Licensing: the open-source clients for this endpoint (borsapy,
isyatirimhisse) state personal/educational use only. Fine for this
single-user tool; a commercial product needs a license.

## Full BIST company list

```
cd apps/api
.venv/bin/python scripts/import_bist_companies.py --dry-run   # inspect
.venv/bin/python scripts/import_bist_companies.py             # writes app/providers/company/bist_companies.json
```

Sources: `GET https://www.kap.org.tr/tr/api/company/generic/excel/IGS/A`
(xlsx: BIST KODU, company title, city) and `https://www.kap.org.tr/tr/Sektorler`
(sector names embedded in the Next.js payload). If KAP blocks scripted
requests, download both in a browser and pass `--from-file` /
`--sectors-from-file`. The JSON records its source URLs and fetch date in
`metadata`; commit it. Re-run when companies list/delist.

## Setting up the credentialed sources

1. **TCMB EVDS**: register at https://evds3.tcmb.gov.tr, generate an API key
   from your profile page, put it in `.env` as `EVDS_API_KEY`.
2. **OpenAI**: create an API key at https://platform.openai.com, put it in
   `.env` as `OPENAI_API_KEY`. Optional `OPENAI_MODEL` (default
   `gpt-4.1-mini`).
3. **Gemini** (free-tier alternative to OpenAI, good for local dev):
   create an API key at https://aistudio.google.com/apikey, put it in
   `.env` as `GEMINI_API_KEY`. Optional `GEMINI_MODEL` (default
   `gemini-3.6-flash`). Only used if `OPENAI_API_KEY` is unset — see
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
