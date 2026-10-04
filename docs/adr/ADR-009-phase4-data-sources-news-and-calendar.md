# ADR-009: Phase 4 data sources (news aggregation, event calendar)

## Status
Accepted — Amends [ADR-002](ADR-002-data-provider-selection.md)

## Context
ADR-002 researched and selected Phase 1's data providers (market data,
financials, KAP disclosures, macro series). Phase 4 added two features with
no provider coverage in ADR-002: a market-wide news feed, and an upcoming-
events calendar (TCMB rate decisions; company dividend/capital-increase/IPO
announcements). Both needed new source research under the same selection
policy ADR-002 established (prefer official APIs, then free reliable
providers, then legally usable public sources, then mock).

## Decision

### News — `GoogleNewsProvider`
Google News RSS search (`news.google.com/rss/search`), no API key. Same
"unofficial but public" posture already accepted for KAP in ADR-002 — a
public, unauthenticated endpoint used for personal/research-scale queries,
not a documented partner API. Live-verified to return real, relevant,
Turkish-language results for BIST tickers. Title-similarity deduplication
(`difflib.SequenceMatcher`, threshold 0.75) collapses the same story
reported by multiple outlets.

### Calendar — two different reliability tiers, kept separate on purpose
- **TCMB PPK (interest rate decision) meeting dates**: genuinely
  forward-looking and official, but TCMB publishes no scrapeable JSON/API
  for its own meeting calendar (confirmed live — only static HTML pages per
  year). Sourced as a manually-maintained, citation-commented snapshot
  (`config/tcmb_calendar.yaml`), updated by hand whenever TCMB publishes a
  new year's calendar.
- **Company events (dividend, capital increase, IPO)**: reuse the existing
  KAP disclosure provider rather than a new source — confirmed live that
  `KapDisclosureProvider`'s `byCriteria` endpoint returns every BIST
  member's disclosures when `mkkMemberOidList` is left empty, not just a
  single company's. `get_market_disclosures()` filters this market-wide
  feed to `DIVIDEND`/`CAPITAL`/`IPO` categories (new `DisclosureCategory.IPO`
  member, keyword-matched on "halka arz"/"izahname" etc.). These are shown
  as **announcement dates**, explicitly labelled as such in the UI — not
  invented future payment/record dates. Fetching exact structured dates
  (e.g. an actual dividend payment date) would require parsing KAP's
  disclosure detail pages, which are a client-rendered SPA with no JSON
  API (confirmed live) — deferred as a V2, not attempted here to avoid the
  "never invent/misparse data" principle being violated by a fragile
  per-template scraper.

## Consequences
- No new paid dependency and no new scraping target beyond what ADR-002
  already accepted (KAP) plus one more "public but unofficial" RSS endpoint
  (Google News) — consistent risk profile with the rest of the project.
- IPO calendar coverage is only as good as KAP's own announcement timing
  and this project's keyword matching — not a dedicated BIST IPO calendar
  source. If that proves insufficient, it's a new, separate data-source
  decision (not a change to this one).
- `ADR-002`'s provider table should be read together with this ADR for a
  complete Phase 1-4 provider picture; ADR-002 itself is not rewritten
  (its Phase 1 research record stays intact) — see its Status line.
