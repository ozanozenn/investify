from __future__ import annotations

from app.llm.base import LLMProvider
from app.schemas.context import StructuredAnalysisContext
from app.schemas.llm_analysis import HorizonOutlook, LLMAnalysisResult

_MOCK_PREFIX = "[MOCK LLM — no OPENAI_API_KEY set] "


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
    """Deterministic, clearly-labeled placeholder used when no
    OPENAI_API_KEY is configured (ADR-002/003). Derives its (simplistic)
    outlook straight from the already-computed overall score so the
    pipeline is exercisable end-to-end without a paid API key — this is
    NOT a substitute for real interpretation and is labeled as such in
    every text field."""

    code = "mock"
    model = "mock-v1"
    is_mock = True

    async def analyze_company(
        self, context: StructuredAnalysisContext, prompt_version: str
    ) -> LLMAnalysisResult:
        if context.unsupported_reason:
            neutral = HorizonOutlook(outlook="NEUTRAL", confidence=0.0, drivers=[], risks=[], catalysts=[])
            return LLMAnalysisResult(
                executive_summary=_MOCK_PREFIX + context.unsupported_reason,
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
        summary = (
            f"{_MOCK_PREFIX}{context.company.name} ({context.ticker}) — overall deterministic "
            f"score {overall}/100. Growth {context.scores.growth.score}, "
            f"Profitability {context.scores.profitability.score}, "
            f"Balance Sheet {context.scores.balance_sheet.score}, "
            f"Cash Flow {context.scores.cash_flow.score}, "
            f"Valuation {context.scores.valuation.score}. "
            "This summary is a deterministic placeholder, not an LLM interpretation."
        )

        def horizon(conf: float) -> HorizonOutlook:
            return HorizonOutlook(
                outlook=outlook,
                confidence=conf,
                drivers=[c.reason for c in context.scores.growth.components if c.value is not None][:3],
                risks=[c.reason for c in context.scores.balance_sheet.components if c.points < c.max_points * 0.5],
                catalysts=[d.title for d in context.disclosures[:2]],
            )

        return LLMAnalysisResult(
            executive_summary=summary,
            short_term=horizon(context.data_quality.overall * 0.6),
            medium_term=horizon(context.data_quality.overall * 0.5),
            long_term=horizon(context.data_quality.overall * 0.4),
            bull_case=[c.reason for c in context.scores.growth.components if c.points >= c.max_points * 0.7],
            bear_case=[c.reason for c in context.scores.balance_sheet.components if c.points < c.max_points * 0.3],
            key_risks=[_MOCK_PREFIX + "See balance sheet and cash flow score components for detail."],
            key_catalysts=[d.title for d in context.disclosures[:3]],
            thesis_breakers=[_MOCK_PREFIX + "Net Debt/EBITDA or margin deterioration beyond current levels."],
            what_to_watch=[_MOCK_PREFIX + "Next quarterly financial report and KAP disclosures."],
        )
