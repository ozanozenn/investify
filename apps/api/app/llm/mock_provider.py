from __future__ import annotations

from app.llm.base import LLMProvider
from app.llm.number_format import format_score
from app.schemas.context import StructuredAnalysisContext
from app.schemas.llm_analysis import HorizonOutlook, LLMAnalysisResult

_MOCK_PREFIX = "[MOCK LLM — OPENAI_API_KEY veya GEMINI_API_KEY tanımlı değil] "


def _outlook_from_score(score: float) -> str:
    if score >= 70:
        return "POSITIVE"
    if score >= 55:
        return "NEUTRAL_POSITIVE"
    if score >= 45:
        return "NEUTRAL"
    if score >= 30:
        return "NEUTRAL_NEGATIVE"
    return "NEGATIVE"


class MockLLMProvider(LLMProvider):
    """Deterministic, clearly-labeled placeholder used when neither
    OPENAI_API_KEY nor GEMINI_API_KEY is configured (ADR-002/003). Derives
    its (simplistic) outlook straight from the already-computed overall
    score and echoes the deterministic verdict's own headline/lens reasons
    so the pipeline is exercisable end-to-end without any LLM key — this
    is NOT a substitute for real interpretation and is labeled as such in
    every text field. Produces the company-analysis-v4 shape."""

    code = "mock"
    model = "mock-v1"
    is_mock = True

    async def analyze_company(
        self,
        context: StructuredAnalysisContext,
        prompt_version: str,
        extra_instructions: str | None = None,
    ) -> LLMAnalysisResult:
        # `extra_instructions` (halüsinasyon düzeltme notu) yok sayılır:
        # mock gerçek bir model çağırmaz, çıktısı zaten deterministik.
        if context.unsupported_reason:
            neutral = HorizonOutlook(
                outlook="NEUTRAL",
                rationale=_MOCK_PREFIX + "Bu sektör için ileriye dönük görünüm üretilmiyor.",
            )
            return LLMAnalysisResult(
                executive_summary=_MOCK_PREFIX + context.unsupported_reason,
                what_matters_now=[],
                short_term=neutral,
                medium_term=neutral,
                long_term=neutral,
                bull_case=[],
                bear_case=[],
                key_risks=[],
                key_catalysts=[],
                thesis_breakers=[],
                what_to_watch=[],
            )

        overall = context.scores.overall
        outlook = _outlook_from_score(overall)
        verdict = context.verdict
        verdict_part = f"Deterministik hüküm: {verdict.headline} " if verdict else ""
        summary = (
            f"{_MOCK_PREFIX}{context.company.name} ({context.ticker}) — {verdict_part}"
            f"Genel deterministik skor {format_score(overall)}. "
            "Bu özet deterministik bir yer tutucudur, gerçek bir yapay zekâ yorumu değildir."
        )

        what_matters_now: list[str] = []
        if verdict is not None:
            what_matters_now += [f"{lens.label}: {lens.reason}" for lens in verdict.lenses if lens.verdict]
        what_matters_now += [d.title for d in context.disclosures[:2]]

        horizon = HorizonOutlook(
            outlook=outlook,
            rationale=_MOCK_PREFIX + f"Genel skora ({format_score(overall)}) dayalı yer tutucu görünüm.",
        )

        return LLMAnalysisResult(
            executive_summary=summary,
            what_matters_now=what_matters_now,
            short_term=horizon,
            medium_term=horizon,
            long_term=horizon,
            bull_case=[c.reason for c in context.scores.growth.components if c.points >= c.max_points * 0.7],
            bear_case=[c.reason for c in context.scores.balance_sheet.components if c.points < c.max_points * 0.3],
            key_risks=[_MOCK_PREFIX + "Ayrıntı için bilanço ve nakit akışı skor bileşenlerine bakın."],
            key_catalysts=[d.title for d in context.disclosures[:3]],
            thesis_breakers=[_MOCK_PREFIX + "Net Borç/FAVÖK'ün yükselmesi veya marjların mevcut seviyenin altına gerilemesi."],
            what_to_watch=[_MOCK_PREFIX + "Bir sonraki çeyrek finansal rapor ve KAP açıklamaları."],
        )
