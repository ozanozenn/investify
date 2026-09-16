# LLM Integration

See [ADR-003](adr/ADR-003-llm-separation.md) for the core "interpretation
only, never computation" architecture decision. This document covers the
operational details.

## Provider abstraction

```
LLMProvider (app/llm/base.py)
    |
    +-- OpenAIProvider   (app/llm/openai_provider.py)  — real, used when OPENAI_API_KEY is set
    +-- GeminiProvider   (app/llm/gemini_provider.py)   — real, free-tier dev alternative, used when
    |                                                      OPENAI_API_KEY is unset but GEMINI_API_KEY is set
    +-- MockLLMProvider  (app/llm/mock_provider.py)     — deterministic fallback if neither is set
```

`services/provider_bundle.py` picks the implementation once, at startup,
based on which key is configured (OpenAI takes priority). Nothing else in
the codebase imports the OpenAI or Gemini SDKs directly.

## OpenAI implementation

- Model: `Settings.openai_model` (default `gpt-4.1-mini` — cheap, supports
  Structured Outputs, sufficient for a single well-scoped analysis prompt).
- Uses the SDK's `beta.chat.completions.parse(..., response_format=LLMAnalysisResult)`
  (Structured Outputs against a Pydantic model) so the response is
  guaranteed to validate against `LLMAnalysisResult`'s schema or the call
  raises — there is no "hope the JSON parses" path.
- Retries transient failures 3x with exponential backoff (`tenacity`).
- A `message.refusal` (the model declining to answer) is treated as a
  hard failure, not silently swallowed.

## Gemini implementation

A free-tier alternative to OpenAI for local development (see
`docs/DATA_SOURCES.md`), used only when `OPENAI_API_KEY` is unset and
`GEMINI_API_KEY` is set.

- Model: `Settings.gemini_model` (default `gemini-2.0-flash`).
- Uses `google-genai`'s `response_schema=LLMAnalysisResult` +
  `response_mime_type="application/json"` to request schema-constrained
  JSON, but — unlike `OpenAIProvider`, which trusts the SDK's own
  `.parsed` convenience — the raw `response.text` is always explicitly
  re-validated with `LLMAnalysisResult.model_validate_json(...)`. A
  malformed or empty response raises `LLMProviderError` (pipeline stage
  marked FAILED), never silently accepted.
- Same retry policy as `OpenAIProvider` (3x, exponential backoff).
- Tested in `tests/unit/test_gemini_provider.py` against a mocked SDK
  client (no real `GEMINI_API_KEY` in CI) — covers valid parse, empty
  response, malformed JSON, schema mismatch, and SDK-level exceptions.

## Mock implementation

Used automatically when neither `OPENAI_API_KEY` nor `GEMINI_API_KEY` is
set. It is **not** a simulated LLM — it deterministically derives an
outlook label from the already-computed `scores.overall` and echoes
score-component reasons / recent KAP titles into the driver/risk/catalyst
fields, with every text field prefixed
`[MOCK LLM — no OPENAI_API_KEY or GEMINI_API_KEY set]`. This exists so
the full pipeline (including the UI) is exercisable and testable without
any paid API key, per roadmap section 92.

## Prompt versioning (section 42/79)

```
apps/api/app/llm/prompts/
  company-analysis-v1.md
```

The prompt file is loaded by name (`Settings.llm_prompt_version`, default
`"company-analysis-v1"`) and that exact string is persisted on every
`AnalysisSnapshot`. Changing the prompt's wording without changing its
*meaning* can stay `v1`; changing what it's asked to produce should bump to
`v2` and add a new file — old snapshots keep referencing `v1` and remain
interpretable.

## Hallucination guard (section 41)

`llm/hallucination_guard.py` is a **heuristic**, not a proof: it
regex-extracts standalone numbers ≥ 1 from the LLM's free-text fields and
flags any that don't approximately match a number present in the
structured context that was sent (2% relative tolerance, with "100" and
4-digit calendar years excluded as known false-positive sources). Flags
are attached to `analysis_json._meta.hallucination_flags` — visible, never
silently dropped or auto-corrected.

## Context (section 39)

The LLM never receives a raw DB dump. `services/context_builder.py`
assembles exactly one `StructuredAnalysisContext` object
(`schemas/context.py`) containing `company`, `market`, `metrics`,
`financial_history`, `valuation`, `scores`, `macro`, `disclosures`,
`data_quality`, `sources`. That object — serialized as-is — is both what
the prompt embeds and what gets persisted as `AnalysisSnapshot.context_json`,
so "what did the LLM actually see" is always reconstructable.
