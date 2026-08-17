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
        self, context: StructuredAnalysisContext, prompt_version: str
    ) -> LLMAnalysisResult: ...
