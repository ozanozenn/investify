# ADR-005: Analysis snapshots as the reproducibility/history backbone

## Status
Accepted (Phase 1)

## Context
Sections 24/25/78/79 treat historical analysis snapshots as one of the most
important features of the whole product (thesis tracking, "what changed",
reproducibility). Phase 1 must lay this foundation even though the
comparison UI itself is deferred to Phase 2.

## Decision
Every `POST /api/companies/{ticker}/refresh` run, on success, writes exactly
one row to `analysis_snapshots` containing:
- `ticker`, `created_at`, `as_of`
- `financial_engine_version`, `scoring_engine_version`,
  `valuation_engine_version`, `prompt_version`, `llm_model`
- `context_json` — the exact `StructuredAnalysisContext` sent to the LLM
- `analysis_json` — the exact validated `LLMAnalysisResult` returned
- `data_quality_json` — completeness/freshness/warnings at that moment

This row is immutable once written (no update path). `GET
/api/companies/{ticker}/analysis` returns the latest snapshot;
`GET /api/companies/{ticker}/analysis/history` (route exists in Phase 1,
returns the list) enables Phase 2's diff UI without a schema change.

## Consequences
- Reproducing "what did the system say about THYAO on 2026-08-17" is a
  single row read, not a re-computation — important because re-computation
  later would use different (updated) financial data and could not
  reproduce the historical view.
- Storage cost is small (one JSONB row per refresh) and acceptable for a
  single-user system with on-demand refresh (no high-frequency polling in
  Phase 1).
