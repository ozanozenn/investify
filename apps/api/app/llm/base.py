from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.context import StructuredAnalysisContext
from app.schemas.llm_analysis import LLMAnalysisResult


class LLMProviderError(Exception):
    pass


class LLMProvider(ABC):
    """LLMProvider abstraction (roadmap section 3 "LLM"): business logic
    never depends on the OpenAI SDK directly, only on this interface."""

    code: str
    model: str
    is_mock: bool = False

    @abstractmethod
    async def analyze_company(
        self,
        context: StructuredAnalysisContext,
        prompt_version: str,
        extra_instructions: str | None = None,
    ) -> LLMAnalysisResult:
        """`extra_instructions`: optional text appended after the prompt
        template — used for the single hallucination-correction retry
        (`services/llm_analysis.py`). Implementations that don't call a
        real model (mock) may ignore it."""
        ...
