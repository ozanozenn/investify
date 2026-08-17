"""Heuristic numeric hallucination guard (ADR-003, roadmap section 41).

Not a proof of correctness — a visibility net. Extracts standalone numbers
from the LLM's free-text fields and flags any that do not appear (within a
small relative tolerance, since the LLM may round) among the numeric leaves
of the context that was actually sent to it. Flags are attached to the
analysis result's metadata for the UI/logs; nothing is silently dropped.
"""

from __future__ import annotations

import re

from app.schemas.context import StructuredAnalysisContext
from app.schemas.llm_analysis import LLMAnalysisResult

_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
_REL_TOLERANCE = 0.02


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

    walk(context.model_dump(mode="json"))
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
        for match in _NUMBER_RE.findall(text):
            try:
                value = float(match.replace(",", "."))
            except ValueError:
                continue
            if abs(value) < 1:  # ratios/percent fragments too noisy to check reliably
                continue
            if value == 100:  # near-universal "score out of 100" denominator, not a data claim
                continue
            if 2000 <= value <= 2099 and "." not in match and "," not in match:  # calendar year
                continue
            if not any(
                ctx_val != 0 and abs(value - ctx_val) / abs(ctx_val) <= _REL_TOLERANCE
                for ctx_val in context_numbers
            ):
                flagged.append(f"unverified number '{match}' in: {text[:120]}")
    return flagged
