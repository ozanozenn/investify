"""Heuristic numeric hallucination guard (ADR-003, roadmap section 41).

Not a proof of correctness — a visibility net. Extracts standalone numbers
from the LLM's free-text fields and flags any that do not appear (within a
small relative tolerance, since the LLM may round) among the numeric leaves
of the context that was actually sent to it. Flags are attached to the
analysis result's metadata for the UI/logs; nothing is silently dropped.
"""

from __future__ import annotations

import re

from app.llm.number_format import extract_number_candidates
from app.schemas.context import StructuredAnalysisContext
from app.schemas.llm_analysis import LLMAnalysisResult

_REL_TOLERANCE = 0.02

# Dates are common inside quoted KAP disclosure titles and — since
# company-analysis-v3 asks the LLM to write in natural, spoken-style
# Turkish — increasingly in prose too (e.g. "23 Eylül 2026 tarihli KAP
# bildirimi"). None of these are numeric claims to verify against the
# context, so they're stripped before number extraction rather than
# taught to the number regex as a special case. Live-verified 2026-09-28:
# without the "DD <Turkish month> YYYY" alternative below, a real Gemini
# response calling out real disclosure dates in prose produced 5
# false-positive hallucination flags on the bare day-of-month digits.
_TR_MONTHS_RE = (
    "Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık"
)
_DATE_RE = re.compile(
    r"\b\d{1,2}-\d{1,2}-\d{4}\b"
    r"|\b\d{4}-\d{1,2}-\d{1,2}\b"
    rf"|\b\d{{1,2}}\s+(?:{_TR_MONTHS_RE})\s+\d{{4}}\b"
)

# Turkish ordinal numbers ("2. Çeyrek" = "2nd Quarter", "3. sırada") use a
# bare digit + period, not a decimal point — e.g. "2026 2. Çeyrek Finansal
# Sonuçlar" would otherwise flag "2" as an unverified number. A decimal
# point is always immediately followed by another digit (`_NUMBER_RE`
# requires this), so a digit-period-whitespace sequence is unambiguously
# an ordinal marker, never a truncated decimal.
_ORDINAL_RE = re.compile(r"\b\d{1,2}\.(?=\s)")


def _collect_context_numbers(context: StructuredAnalysisContext) -> list[float]:
    numbers: list[float] = []

    def walk(obj) -> None:
        if isinstance(obj, bool):
            return
        if isinstance(obj, (int, float)):
            numbers.append(float(obj))
        elif isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    # Hüküm (ADR-011) LLM prompt'una girmiyor; onun sayıları LLM'i "doğrulamamalı".
    walk(context.model_dump(mode="json", exclude={"verdict"}))
    return numbers


def _text_fields(result: LLMAnalysisResult) -> list[str]:
    texts = [result.executive_summary]
    for horizon in (result.short_term, result.medium_term, result.long_term):
        texts += horizon.drivers + horizon.risks + horizon.catalysts
    texts += result.bull_case + result.bear_case + result.key_risks
    texts += result.key_catalysts + result.thesis_breakers + result.what_to_watch
    return texts


def find_unsupported_numbers(context: StructuredAnalysisContext, result: LLMAnalysisResult) -> list[str]:
    context_numbers = _collect_context_numbers(context)
    flagged: list[str] = []
    for text in _text_fields(result):
        cleaned = _ORDINAL_RE.sub(" ", _DATE_RE.sub(" ", text))
        for literal, candidates in extract_number_candidates(cleaned):
            candidates = [c for c in candidates if c != 100]  # score-out-of-100 denominator, not a data claim
            if not candidates:
                continue
            if len(candidates) == 1 and "." not in literal and "," not in literal and 2000 <= candidates[0] <= 2099:
                continue  # calendar year
            if all(abs(c) < 1 for c in candidates):
                continue  # bare small fragments too noisy to check reliably
            supported = any(
                ctx_val != 0 and abs(c - ctx_val) / abs(ctx_val) <= _REL_TOLERANCE
                for c in candidates
                for ctx_val in context_numbers
            )
            if not supported:
                flagged.append(f"unverified number '{literal}' in: {text[:120]}")
    return flagged
