# Roadmap

Full product vision: `MAIN_ROADMAP.md` (repo root). This document tracks
phase-level status. Phase boundaries follow the roadmap's own "57.
GELİŞTİRME STRATEJİSİ" / "PHASE 1" addendum.

## Phase 1 — MVP Vertical Slice — ✅ DONE (this delivery)

Ticker search → real company/financial/KAP/macro data → deterministic
metrics/valuation/scoring → structured LLM interpretation → persisted,
versioned analysis snapshot → Company Detail UI. Full scope boundary and
Definition of Done: [docs/PHASE_1_SCOPE.md](PHASE_1_SCOPE.md).

## Phase 2 — Deepen valuation & history — ✅ DONE

- DCF engine (Bear/Base/Bull scenarios, WACC × terminal-growth sensitivity
  matrix, user-overridable assumptions) — `app/valuation_engine/dcf.py`.
- Historical analysis comparison ("Since previous analysis") —
  `app/services/snapshot_diff.py`, no schema change (ADR-005 held).
- Peer comparison (sector/industry median) — `app/services/peer_comparison.py`;
  required fixing a real sector/industry taxonomy mismatch between the
  curated seed and live yfinance bootstraps (`providers/company/taxonomy.py`).
- Thesis tracking (STRENGTHENED/WEAKENED/UNCHANGED verdict), same service.
- Also delivered alongside Phase 2: Google Gemini as a free-tier LLM
  provider (`llm/gemini_provider.py`), a live TCMB EVDS2→EVDS3 migration
  fix (`providers/macro/evds_client.py`), and a **full Turkish
  localization pass** — UI, LLM output (`company-analysis-v2.md`), error
  messages, and config-driven labels. All future features ship in Turkish
  from the first draft (no English-then-translate).

## Phase 3 — Sector-specific engines (deferred — user decision 2026-09-17)

Explicitly skipped for now: the user wants to keep the system's
technical-metric surface minimal at its current scope and revisit
whether more sector-specific metrics are worth the added complexity
later, rather than build it speculatively now.

- Bank-specific financial engine (NIM, loan/deposit growth, NPL, CAR,
  cost/income) — currently explicitly refused with an "unsupported"
  state (`financial_engine/industry_strategy.py`) rather than a wrong
  generic score. Given how much of BIST's market cap is banks, this
  would likely be the highest-value item if/when this phase is revisited.
- REIT/GYO (NAV, NAV discount, occupancy) and Holding (SOTP, holding
  discount) engines.

## Phase 4 — News, watchlist, alerts (in progress — news + calendar + watchlist done)

- ✅ **News aggregation** — `app/providers/news/google_news_provider.py`
  (Google News RSS search, no API key), title-similarity dedup. No
  clustering or sentiment scoring in this pass (user decision 2026-09-17:
  minimal first, add later if wanted); stateless endpoint
  (`GET /api/companies/{ticker}/news`), not persisted, not wired into the
  LLM context — independent of the financial-analysis pipeline.
- ✅ **Site navigation + market-wide "Haberler" page** (2026-09-28) —
  `components/nav-bar.tsx` (Ana Sayfa / Haberler / Takvim, on every page),
  `/haberler` combining `GET /api/market/disclosures` (KAP market-wide feed
  — live-verified an empty `mkkMemberOidList` returns every BIST member's
  disclosures, not just tracked companies) with `GET /api/market/news`
  (general "Borsa İstanbul" Google News query). Fixed a real KAP
  categorization bug while wiring this up: `categorize()` only looked at
  the `subject` field, which is often a generic regulatory template name
  ("Özel Durum Açıklaması (Genel)") — the real signal (e.g. "Pay Geri Alım
  İşlemleri") is frequently only in the free-text summary/title. Now checks
  both; also affects the existing per-company KAP list
  (`services/persistence.py`). Also tightened the `CAPITAL` keyword from a
  bare "sermaye" (false-matched "Sermaye Piyasası Aracı" bond/coupon
  disclosures) to "sermaye artır/azalt" + "bedelli"/"bedelsiz".
- ✅ **Takvim (calendar), V1 scope** (2026-09-28, user decision) —
  `GET /api/calendar`: TCMB PPK faiz kararı tarihleri (real, forward-looking,
  from `config/tcmb_calendar.yaml` — TCMB publishes no scrapeable JSON/API
  for this, so it's a manually-sourced, citation-commented snapshot updated
  when TCMB publishes a new year's calendar) + KAP market-wide disclosures
  filtered to DIVIDEND/CAPITAL/IPO (new `DisclosureCategory.IPO`, keywords
  "halka arz"/"izahname"). Deliberately does **not** attempt to parse exact
  future payment/record dates out of KAP disclosure detail pages — that
  page is a client-rendered SPA with no JSON API (confirmed live), and
  per-template scraping was explicitly deferred by the user in favor of a
  fast, honest V1 that shows announcement dates as what they are (labelled
  in the UI), not invented execution dates. IPO calendar reuses the same
  KAP market feed rather than a separate scraper (no dedicated BIST IPO
  data source integrated). V2 (per-template detail-page parsing for exact
  dates) is a candidate future iteration, not started.
- ✅ **Watchlist + scheduled refresh + home dashboard** (2026-10-27,
  ADR-013) — `watchlist_items` table, `/api/watchlist` CRUD with a
  server-built summary (price, verdict incl. demo signal, overall score and
  change vs. previous snapshot, last refresh, last job failure), weekday
  after-close in-process scheduler + "Şimdi yenile" manual trigger, home
  page "İzleme Listem" + TCMB/KAP market strip, add/remove toggle on the
  company page.
- Alert engine (score change, new important KAP, valuation threshold) —
  not started (user decision 2026-09-17: "anlık bildirim" explicitly
  deferred, not needed right now).
- Context-aware AI chat per company (RAG or structured-context-only,
  per roadmap section 83 — must not answer from uncontrolled internet
  knowledge) — not started.

## Kalite ve okunabilirlik turu (2026-09-28, user-directed, feature freeze)

Not a new phase — the user paused new features to focus on data accuracy
and LLM output quality of what already exists, per an explicit "onayıma
kadar extra feature eklemeyeceğiz" instruction.

- ✅ **Data-accuracy audit** — an independent agent cross-checked 19
  ASELS analysis numbers against live `yfinance` data using the app's own
  formulas. 18/19 reproduced exactly (deterministic engines are solid);
  found one real bug: an LLM-generated free cash flow figure with a
  flipped sign, undetected because the hallucination guard's number regex
  couldn't parse grouped-thousands numbers. See `docs/TECHNICAL_DEBT.md`
  for the full root-cause writeup.
- ✅ **LLM prompt rewritten (`company-analysis-v3.md`)** from a structured
  10-question conversation with the user about desired output: numbers
  now pre-formatted and used sparingly (not a stat dump), conversational-
  advisor tone, jargon explained in plain language with the abbreviation
  in parentheses, missing data stated explicitly ("bu konuda yorum
  yapamıyoruz"), scores always paired with a plain-language interpretation,
  and genuine scenario-based short/medium/long-term outlook referencing
  real dates (a new `next_rate_decision_date` context field, sourced from
  the Takvim feature's TCMB calendar config) instead of ever inventing one.
  Still no BUY/SELL/HOLD or target price under any framing.
- ✅ **Number formatting moved to the deterministic layer**
  (`llm/number_format.py`, `llm/context_formatter.py`) — the LLM now
  receives (and must reproduce verbatim, sign included) human-readable
  Turkish-formatted numbers instead of raw floats.
- ✅ **Hallucination guard rewritten** to parse the formatted numbers above
  (grouped thousands, `%`/`x`/`milyar`/`milyon`/`bin` suffixes, Turkish-
  convention sign-before-percent) instead of a naive per-character-group
  regex. Live-verified against real Gemini output: 0 flags on a
  well-formed analysis, correctly flags an injected sign-flip.
- Not done: making `hallucination_flags` blocking/retry-triggering
  (still advisory-only/logged) or surfacing them in the frontend UI —
  both noted as candidate follow-ups, not requested yet.

## Phase 5+ — Advanced

Consensus analyst data (if a legally usable source is found), management
guidance vs. actual tracking, capital allocation engine, accounting
anomaly detection beyond the current absence, full Turkey macro dashboard,
technical analysis indicator set, analysis outcome tracking (not
backtesting — roadmap section 44 is explicit this is not a trading bot).

## Explicit non-goals (forever)

Portfolio management, broker integration, automatic trading. See
`MAIN_ROADMAP.md` section 1. BUY/SELL/HOLD: a deterministic AL/TUT/SAT
signal exists **as a demo only** (user decision 2026-10-12, ADR-011),
off with one config flag; the LLM never produces one.
