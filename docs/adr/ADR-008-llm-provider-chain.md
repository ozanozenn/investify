# ADR-008: LLM provider chain (OpenAI → Gemini → Mock)

## Status
Accepted (Phase 2)

## Context
[ADR-003](ADR-003-llm-separation.md) fixes the LLM's *role* (interpretation
only). This ADR covers which LLM actually fills that role at runtime.
OpenAI was the original Phase 1 choice, but it's a paid API — for ongoing
local development and for anyone running this project without a budget for
API calls, a free-tier alternative mattered enough to add one (Google
Gemini has a usable free tier). The project also already had a
`MockLLMProvider` so the pipeline is fully exercisable with zero API keys
at all.

## Decision
- `LLMProvider` (`app/llm/base.py`) is the single abstract contract:
  structured `StructuredAnalysisContext` in, validated `LLMAnalysisResult`
  out. `OpenAIProvider`, `GeminiProvider`, and `MockLLMProvider` all
  implement it identically from the caller's point of view
  (`services/refresh_pipeline.py` never branches on which one is active).
- Selection is automatic, by which API key is configured
  (`services/provider_bundle.py:build_provider_bundle`):
  1. `OPENAI_API_KEY` set → `OpenAIProvider` (paid, production default).
  2. Else `GEMINI_API_KEY` set → `GeminiProvider` (free-tier dev
     alternative).
  3. Else → `MockLLMProvider` (deterministic, every text field prefixed
     `[MOCK LLM — ...]`, derives its outlook straight from the
     already-computed `scores.overall` so the full pipeline — including the
     UI — is exercisable and testable with no key at all).
- The two real providers differ in how much they trust their SDK:
  `OpenAIProvider` uses Structured Outputs (`response_format=
  LLMAnalysisResult`) and trusts the SDK's own `message.parsed` convenience
  (the SDK validates against the schema before returning it — a `message.
  refusal` is treated as a hard failure, not silently swallowed).
  `GeminiProvider` does **not** extend the same trust to its SDK: `google-
  genai`'s `.parsed` convenience isn't reliably present across SDK
  versions, so the raw `response.text` is always explicitly re-validated
  with `LLMAnalysisResult.model_validate_json(...)` regardless of what the
  SDK itself claims to have parsed. Either provider's failure mode raises
  `LLMProviderError`, marking the pipeline stage `FAILED` — never silently
  accepted.
- Both retry transient failures 3x with exponential backoff (`tenacity`).

## Consequences
- Switching LLM vendor (or going keyless for a demo) is a `.env` change,
  never a code change.
- Two SDKs (`openai`, `google-genai`) are maintained in parallel —
  accepted cost for not being locked to one paid vendor during active
  development.
- Prompt content itself is versioned independently of provider choice
  (`llm_prompt_version`, filename-based — see `docs/LLM.md`); both real
  providers load and render the same prompt template, so a prompt change
  doesn't need to be duplicated per provider.
