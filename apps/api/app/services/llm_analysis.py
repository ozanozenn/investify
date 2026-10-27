"""LLM yorum aşaması + tek seferlik halüsinasyon düzeltmesi (ADR-003).

`refresh_pipeline.py` LLM'i doğrudan değil, bunun üzerinden çağırır:

1. LLM bir kez çağrılır, `find_unsupported_numbers` çalışır.
2. Context'te karşılığı olmayan sayı varsa LLM **bir kez** daha çağrılır;
   prompt'un sonuna o sayıları listeleyen kısa bir düzeltme notu eklenir.
3. Hangisinin bayrağı daha azsa o tutulur (eşitlikte ilk yanıt — düzeltme
   bir şey kazandırmadıysa doğal yanıt kalır).

Guard hâlâ yalnızca **uyarıdır**: bayrak kalsa da analiz kaydedilir,
bayraklar `_meta`'ya yazılır ve arayüzde gösterilir. Düzeltme çağrısı
hata verirse ilk (geçerli) yanıt kullanılır — refresh bozulmaz. İlk
çağrının hatası ise eskisi gibi yukarı fırlatılır.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.llm.base import LLMProvider, LLMProviderError
from app.llm.hallucination_guard import build_correction_instructions, find_unsupported_numbers
from app.schemas.context import StructuredAnalysisContext
from app.schemas.llm_analysis import LLMAnalysisResult

logger = get_logger(__name__)


@dataclass
class GuardedAnalysis:
    result: LLMAnalysisResult
    hallucination_flags: list[str]
    hallucination_retry: bool
    hallucination_flags_first_attempt: list[str]
    retry_error: str | None = None

    def meta(self) -> dict:
        """`analysis_json._meta`'ya eklenen halüsinasyon alanları."""
        meta: dict = {
            "hallucination_flags": self.hallucination_flags,
            "hallucination_retry": self.hallucination_retry,
            "hallucination_flags_first_attempt": self.hallucination_flags_first_attempt,
        }
        if self.retry_error is not None:
            meta["hallucination_retry_error"] = self.retry_error
        return meta


async def analyze_with_hallucination_retry(
    llm: LLMProvider,
    context: StructuredAnalysisContext,
    prompt_version: str,
) -> GuardedAnalysis:
    first = await llm.analyze_company(context, prompt_version)
    first_flags = find_unsupported_numbers(context, first)
    if not first_flags:
        return GuardedAnalysis(first, [], False, [])

    logger.warning(
        "llm_hallucination_retry",
        extra={"ticker": context.ticker, "flag_count": len(first_flags)},
    )
    try:
        second = await llm.analyze_company(
            context, prompt_version, extra_instructions=build_correction_instructions(first_flags)
        )
    except LLMProviderError as exc:
        logger.warning("llm_hallucination_retry_failed", extra={"ticker": context.ticker, "error": str(exc)})
        return GuardedAnalysis(first, first_flags, True, first_flags, retry_error=str(exc))

    second_flags = find_unsupported_numbers(context, second)
    if len(second_flags) < len(first_flags):
        return GuardedAnalysis(second, second_flags, True, first_flags)
    return GuardedAnalysis(first, first_flags, True, first_flags)
