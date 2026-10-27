"""Heuristic numeric hallucination guard (ADR-003, roadmap section 41).

Not a proof of correctness — a visibility net. Extracts standalone numbers
from the LLM's free-text fields and flags any that do not appear (within a
small relative tolerance, since the LLM may round) among the numeric leaves
of the context that was actually sent to it. Flags are attached to the
analysis result's metadata for the UI/logs; nothing is silently dropped.

Since company-analysis-v4 a non-empty flag list triggers exactly one
corrective retry (`services/llm_analysis.py`, using
`build_correction_instructions`); the guard itself stays advisory and
never blocks persisting an analysis.
"""

from __future__ import annotations

import re

from app.llm.context_formatter import format_context_for_prompt
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

# Prompt'taki tarih/kimlik alanları: içlerindeki rakamlar veri değildir.
_NON_NUMERIC_KEYS = frozenset(
    {"as_of", "observation_date", "published_at", "fetched_at", "source_url", "ticker", "code"}
)
_ISO_OR_URL_RE = re.compile(
    r"https?://\S+"
    r"|\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?\b"
)


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

    # Ham değerler (hüküm hariç: ham oranları prompt'a hiç gitmiyor).
    walk(context.model_dump(mode="json", exclude={"verdict"}))

    # LLM'in prompt'ta GERÇEKTEN gördüğü biçimlendirilmiş metinlerdeki sayılar
    # da "context'te var" sayılır. Gerekçe: küçük yüzdeler tek ondalıkla
    # yazılır (0,0175 → "%1,8"); ham değere göre yuvarlama farkı %2
    # toleransı aşar ve LLM'in birebir aktardığı doğru rakam yanlışlıkla
    # bayraklanırdı (ROA, reel büyüme, kalite bayrağı marjları). Hükmün
    # başlık/gerekçe metinleri de bu yolla kapsanır.
    # Zaman damgaları/URL'ler sayı iddiası değildir; dahil edilirse dakika/
    # saniye rakamları (ör. "01:42:07") uydurma bir "42,7"yi "context'te
    # var" gösterirdi — saate bağlı, kararsız bir delik.
    def walk_text(obj, key: str | None = None) -> None:
        if key in _NON_NUMERIC_KEYS:
            return
        if isinstance(obj, str):
            cleaned = _ORDINAL_RE.sub(" ", _DATE_RE.sub(" ", _ISO_OR_URL_RE.sub(" ", obj)))
            for _literal, candidates in extract_number_candidates(cleaned):
                numbers.extend(candidates)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                walk_text(v, k)
        elif isinstance(obj, list):
            for v in obj:
                walk_text(v, key)

    walk_text(format_context_for_prompt(context))
    return numbers


def _text_fields(result: LLMAnalysisResult) -> list[str]:
    # company-analysis-v4 şekli: ufuk başına tek `rationale`, ayrıca
    # `what_matters_now`. Her serbest metin alanı kontrol edilir.
    texts = [result.executive_summary, *result.what_matters_now]
    for horizon in (result.short_term, result.medium_term, result.long_term):
        texts.append(horizon.rationale)
    texts += result.bull_case + result.bear_case + result.key_risks
    texts += result.key_catalysts + result.thesis_breakers + result.what_to_watch
    return texts


def _flag(literal: str, text: str) -> str:
    return f"unverified number '{literal}' in: {text[:120]}"


# `_flag`'in tersi — biçim ile ayrıştırıcı yan yana dursun ki biri
# değişip öbürü unutulmasın (`number_format.py` ile aynı ilke). Frontend
# (`apps/web/lib/analysis.ts`) da aynı kalıpla sayıyı okur.
_FLAG_LITERAL_RE = re.compile(r"^unverified number '([^']*)'")

_MAX_LITERALS_IN_CORRECTION = 10


def flagged_literals(flags: list[str]) -> list[str]:
    """Bayraklardaki sayı metinleri, sırası korunarak ve tekrarsız."""
    out: list[str] = []
    for flag in flags:
        match = _FLAG_LITERAL_RE.match(flag)
        literal = match.group(1) if match else None
        if literal and literal not in out:
            out.append(literal)
    return out


def build_correction_instructions(flags: list[str]) -> str:
    """Tek seferlik düzeltme denemesinde prompt'un sonuna eklenen kısa not
    (ADR-003). Sadece hangi sayıların desteksiz olduğunu söyler; doğru
    değeri LLM'e biz söylemeyiz — context zaten elinde."""
    literals = flagged_literals(flags)[:_MAX_LITERALS_IN_CORRECTION]
    listed = ", ".join(f"«{lit}»" for lit in literals)
    return (
        "## Düzeltme talebi\n\n"
        f"Önceki yanıtında context'te karşılığı bulunmayan şu sayılar vardı: {listed}.\n"
        "Yanıtı aynı şemayla baştan üret. Bu kez:\n"
        "- Yalnızca context'te yazan rakamları, context'teki biçimiyle (işaret ve birim dahil) aynen kullan.\n"
        "- Kendi hesabını yapma: rakamları toplama, çıkarma, oranlama, yuvarlama.\n"
        "- Bir rakamdan emin değilsen sayı vermeden sözle anlat."
    )


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
                flagged.append(_flag(literal, text))
    return flagged
