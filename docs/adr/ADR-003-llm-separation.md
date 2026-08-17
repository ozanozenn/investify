# ADR-003: LLM is interpretation-only, never computation

## Status
Accepted (Phase 1)

## Context
Section 2 of the roadmap is explicit and non-negotiable: the LLM must never
compute financial ratios, invent prices, or fabricate sourced facts. This is
the single most important architectural constraint of the whole project.

## Decision
1. All numbers the LLM ever sees come from `services/context_builder.py`,
   which assembles a single `StructuredAnalysisContext` Pydantic object out
   of already-persisted, already-computed DB rows (financial statements,
   `financial_engine` output, `scoring_engine` output, `valuation_engine`
   output, macro observations, KAP disclosures). The LLM layer has no DB
   session and no provider access (enforced by ADR-001's import rule).
2. The prompt (`llm/prompts/company_analysis_v1.md`) instructs the model to
   only use figures present in the supplied context and to leave a field
   empty/omit a claim rather than invent one.
3. The LLM's only contract is: structured context in (typed) → structured
   analysis out (typed, `LLMAnalysisResult`, validated with Pydantic against
   a JSON Schema passed to OpenAI Structured Outputs). If validation fails,
   the pipeline stage is marked `FAILED`, not silently patched.
4. A lightweight post-hoc numeric guard
   (`llm/hallucination_guard.py`) regex-extracts standalone numbers from the
   LLM's free-text fields (`executiveSummary`, reasoning/driver strings) and
   flags (does not silently drop — flags, so it is visible) any number that
   does not appear anywhere in the numeric leaves of the context that was
   sent. This is a heuristic safety net, not a proof; documented as such.

## Consequences
- Every LLM output can be traced back to the exact structured context that
  produced it because the context (with its version/hash) is persisted in
  `analysis_snapshots.context_json` alongside the LLM output.
- Prompt changes are versioned by filename (`_v1`, `_v2`, ...) and the
  version string is stored per snapshot (section 42/79 of the roadmap).
