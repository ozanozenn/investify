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

`analyze_company(context, prompt_version, extra_instructions=None)` —
`extra_instructions` is only used for the single hallucination-correction
retry (see below). Both real providers build their prompt through
`prompt_loader.render_prompt()`, which embeds the formatted context and
appends `extra_instructions` last; the mock ignores it.

The pipeline never calls the provider directly:
`services/llm_analysis.py:analyze_with_hallucination_retry()` wraps the call
with the guard + one retry and returns the result plus the `_meta` fields.

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
  response, malformed JSON, schema mismatch, a pre-v4-shaped response
  being rejected, `extra_instructions` reaching the prompt, and SDK-level
  exceptions.

## Mock implementation

Used automatically when neither `OPENAI_API_KEY` nor `GEMINI_API_KEY` is
set. It is **not** a simulated LLM — it deterministically derives an
outlook label from the already-computed `scores.overall`, echoes the
verdict headline and the reasons of the verdict lenses that voted into
`executive_summary` / `what_matters_now`, and score-component reasons /
recent KAP titles into the lists, with every text field prefixed
`[MOCK LLM — OPENAI_API_KEY veya GEMINI_API_KEY tanımlı değil]`. This
exists so the full pipeline (including the UI) is exercisable and testable
without any paid API key, per roadmap section 92.

## Output schema (company-analysis-v4)

`schemas/llm_analysis.py:LLMAnalysisResult` — deliberately small, so the
model spends its (more expensive) output tokens on explanation, not on
filling redundant lists:

| Field | Shape | Purpose |
|-------|-------|---------|
| `executive_summary` | 2-4 sentences | explains the deterministic verdict |
| `what_matters_now` | ≤ 5, most important first | the "ŞU AN ÖNEMLİ OLANLAR" card |
| `short_term` / `medium_term` / `long_term` | `{outlook: enum, rationale: str}` | one conditional scenario per horizon |
| `bull_case` / `bear_case` | ≤ 3 each | traceable to a context field |
| `key_risks` / `key_catalysts` | ≤ 4 each | |
| `thesis_breakers` | ≤ 3 | concrete, checkable, thresholds only from context |
| `what_to_watch` | ≤ 4 | |

Removed vs. v1-v3: per-horizon `drivers`/`risks`/`catalysts` (redundant
with the top-level lists) and the LLM's own `confidence` number (ADR-003:
the LLM never produces numbers; reliability comes from the verdict card,
ADR-011). `outlook` is now a JSON-Schema enum.

The item limits (`MAX_ITEMS`) are stated in the prompt and in each field's
schema `description`, but are **not** emitted as `maxItems` (support
differs across OpenAI Structured Outputs / Gemini `response_schema`
versions). Over-long lists are trimmed by a Pydantic validator — first
items kept, since the prompt asks for most-important-first — instead of
failing the whole LLM stage. Schema classes use comments, not docstrings,
because Pydantic would otherwise ship the docstrings to the model as
schema descriptions on every call.

Old snapshots are not migrated (ADR-005): `analysis_json` is served as a
plain dict and the frontend renders whichever shape exists
(`apps/web/lib/analysis.ts`, `components/outlook-card.tsx`; TS types mark
both shapes' fields optional).

## Prompt versioning (section 42/79)

```
apps/api/app/llm/prompts/
  company-analysis-v1.md   — original, English "reproduce numbers as plain decimals" convention
  company-analysis-v2.md   — Turkish output (2026-09), numbers still plain decimals
  company-analysis-v3.md   — (2026-09-28): pre-formatted numbers,
                             conversational advisor tone, scenario-based short/medium/
                             long-term outlook, sparse number usage — see below
  company-analysis-v4.md   — current default (2026-10): explains the deterministic
                             verdict (never contradicts/recomputes it, never repeats the
                             demo signal), slim output schema (see above), keeps v3's
                             tone and number rules
```

v1-v3 stay on disk because snapshots reference them by name (audit
trail); they describe the pre-v4 output shape, so only v4 matches the
current `LLMAnalysisResult` schema — don't switch back to them without
also restoring that schema.

The prompt file is loaded by name (`Settings.llm_prompt_version`, default
`"company-analysis-v4"`) and that exact string is persisted on every
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

### Verdict in the prompt (v4)

Since v4 the deterministic verdict (ADR-011) is part of the prompt
context, formatted by `llm/verdict_formatter.py`: `headline`, Turkish
`price`/`quality`/`confidence` labels (Ucuz/Makul/Pahalı, Güçlü/Orta/Zayıf,
Yüksek/Orta/Düşük), and each lens's `label` + `verdict` + engine-written
`reason`. Raw ratios (`lens.value`, `agreement`) are **not** sent — the
reason sentence already carries the formatted percentage. The signal is
sent only as `demo_signal` with an explicit "demo, not advice, don't
repeat" note; the prompt forbids the LLM from giving its own AL/SAT/TUT or
target price. Old snapshots without a verdict format as `"verdict": null`.

## Hallucination guard (section 41)

`llm/hallucination_guard.py` is a **heuristic**, not a proof: it extracts
numeric tokens from the LLM's free-text fields and flags any that don't
approximately match a number present in the structured context that was
sent (2% relative tolerance, with "100" and 4-digit calendar years
excluded as known false-positive sources). Flags are attached to
`analysis_json._meta.hallucination_flags` — visible, never silently
dropped. Checked fields (v4): `executive_summary`, `what_matters_now`, each
horizon's `rationale`, and all six lists. Verdict numbers count as
"in context" only as they appear in the verdict text the LLM actually saw
(headline + lens reasons, e.g. "medyanının %12 üstünde"), not via the
verdict's raw ratio fields.

**One corrective retry (v4).** If the first answer has any flag,
`services/llm_analysis.py` calls the LLM exactly once more with
`hallucination_guard.build_correction_instructions(flags)` appended to the
prompt (lists the unsupported numbers, repeats "use context numbers
verbatim, don't compute"). The answer with fewer flags is kept (tie → the
first). If the retry call itself fails, the first answer is kept. Still
advisory: the analysis is always persisted. `_meta` records:

- `hallucination_flags` — flags of the kept answer
- `hallucination_retry` — whether a retry was made
- `hallucination_flags_first_attempt` — flags of the first answer
- `hallucination_retry_error` — only present if the retry call failed

Cost: a flagged refresh costs at most two LLM calls. The UI
(`components/hallucination-warning.tsx`) shows a Turkish warning with the
flagged numbers inside the "Yapay Zekâ Özeti" card, only when the final
flag list is non-empty (it parses the literal out of the `'…'` in the flag
string — same pattern as `hallucination_guard._FLAG_LITERAL_RE`).

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
`data_quality`, `sources`, `next_rate_decision_date`, `verdict`. That raw object is
what gets persisted as `AnalysisSnapshot.context_json`; the *formatted*
version of it (see above) is what the prompt actually embeds.
