from __future__ import annotations

from pydantic import BaseModel, Field


class HorizonOutlook(BaseModel):
    outlook: str = Field(description="One of: POSITIVE, NEUTRAL_POSITIVE, NEUTRAL, NEUTRAL_NEGATIVE, NEGATIVE")
    confidence: float = Field(ge=0.0, le=1.0)
    drivers: list[str]
    risks: list[str]
    catalysts: list[str]


class LLMAnalysisResult(BaseModel):
    """Structured LLM output (roadmap section 40 / 3.11). Validated with
    Pydantic against the JSON Schema sent to OpenAI Structured Outputs —
    if this fails to parse, the pipeline stage is marked FAILED (ADR-003),
    never silently patched."""

    executive_summary: str
    short_term: HorizonOutlook
    medium_term: HorizonOutlook
    long_term: HorizonOutlook
    bull_case: list[str]
    bear_case: list[str]
    key_risks: list[str]
    key_catalysts: list[str]
    thesis_breakers: list[str]
    what_to_watch: list[str]
