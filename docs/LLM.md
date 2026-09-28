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

- Model: `Settings.gemini_model` (default `gemini-3.6-flash`).
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
  company-analysis-v1.md   — original, English "reproduce numbers as plain decimals" convention
  company-analysis-v2.md   — Turkish output (2026-09), numbers still plain decimals
  company-analysis-v3.md   — current default (2026-09-28): pre-formatted numbers,
                             conversational advisor tone, scenario-based short/medium/
                             long-term outlook, sparse number usage — see below
```

The prompt file is loaded by name (`Settings.llm_prompt_version`, default
`"company-analysis-v3"`) and that exact string is persisted on every
`AnalysisSnapshot`. Changing the prompt's wording without changing its
*meaning* can stay on the same version; changing what it's asked to
produce bumps the version and adds a new file — old snapshots keep
referencing their original version and remain interpretable.

v3 was written directly from a structured 10-question conversation with
the product owner about desired LLM output style (audience, tone, number
density, jargon handling, missing-data phrasing, forward-looking content)
— see `docs/TECHNICAL_DEBT.md` for the full before/after rationale and the
real data-accuracy bug this session also found and fixed (an LLM sign-flip
on a free cash flow figure).

## Number formatting for the prompt (`llm/number_format.py`, `llm/context_formatter.py`)

Every numeric leaf in `StructuredAnalysisContext` is a plain, unrounded
float — correct for the frontend (which formats numbers itself) but
unreadable if handed to an LLM verbatim (`0.8259859533087344` instead of
"82,6%"). v1/v2 deliberately told the LLM to reproduce numbers exactly as
given specifically *because* they were unformatted plain decimals — safe
to verify, unreadable to a human.

v3 flips this: `context_formatter.format_context_for_prompt()` converts
the context into human-readable Turkish strings (`%82,6`, `56,7x`,
`48,9 milyar TL`, `66,5/100`) *before* it reaches the LLM, using a
per-field style map (ratio→percent, P/E-style→multiple, revenue/EBITDA/
cash-flow→compact currency, TCMB rate vs. FX rate handled differently
since one is already percent-scale and the other isn't, etc.). The LLM is
instructed to reproduce these formatted strings exactly, sign included —
never to reformat or recompute them itself.

`render_context_json()` (used by both `OpenAIProvider` and
`GeminiProvider`) is what actually gets embedded in the prompt in place of
`{context_json}`. **This is not what gets persisted** as
`AnalysisSnapshot.context_json` — that field still stores
`context.model_dump(mode="json")`, the raw unformatted object, since it's
the reproducibility/audit record (ADR-005) and a display-formatted string
is a lossy derivative of it, not a better ground truth. "What the LLM
actually saw" for a given snapshot is `render_context_json()` applied to
that raw persisted object, not the object itself.

Also added: `next_rate_decision_date` on `StructuredAnalysisContext`
(populated in `refresh_pipeline.py` from `config/tcmb_calendar.yaml`) — one
concrete, real near-term date the LLM can cite in `what_to_watch`/horizon
scenarios instead of ever inventing one.

## Hallucination guard (section 41)

`llm/hallucination_guard.py` is a **heuristic**, not a proof: it extracts
numeric tokens from the LLM's free-text fields and flags any that don't
approximately match a number present in the structured context that was
sent (2% relative tolerance, with "100" and 4-digit calendar years
excluded as known false-positive sources). Flags are attached to
`analysis_json._meta.hallucination_flags` — visible, never silently
dropped or auto-corrected.

As of v3, number extraction (`number_format.extract_number_candidates`)
has to undo everything `context_formatter` can produce: grouped thousands
("10.733.502.000"), a leading Turkish-style percent sign with the sign
before it ("-%5,9"), and "milyar"/"milyon"/"bin"/"x"/"kat" suffixes — a
percent match produces *two* candidate values (÷100 and as-is) since the
same "%" style is used for both 0-1-scale ratio fields and already-percent
-scale fields like the TCMB policy rate, and the guard can't tell which
field a given LLM sentence is about. Two real bugs were found and fixed
here live (2026-09-28): the old plain regex split large grouped numbers at
every thousands separator (so it never actually checked the real value —
this is how an LLM sign-flip on FCF slipped through undetected), and
`_DATE_RE` didn't recognize dates spelled out in natural Turkish ("23
Eylül 2026"), which v3's more conversational tone made common and which
produced false-positive flags on the bare day-of-month digit.

## Context (section 39)

The LLM never receives a raw DB dump. `services/context_builder.py`
assembles exactly one `StructuredAnalysisContext` object
(`schemas/context.py`) containing `company`, `market`, `metrics`,
`financial_history`, `valuation`, `scores`, `macro`, `disclosures`,
`data_quality`, `sources`, `next_rate_decision_date`. That raw object is
what gets persisted as `AnalysisSnapshot.context_json`; the *formatted*
version of it (see above) is what the prompt actually embeds.
