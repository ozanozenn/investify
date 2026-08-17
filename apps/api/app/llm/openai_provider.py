from __future__ import annotations

from pathlib import Path

from openai import AsyncOpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.llm.base import LLMProvider, LLMProviderError
from app.schemas.context import StructuredAnalysisContext
from app.schemas.llm_analysis import LLMAnalysisResult

logger = get_logger(__name__)
_PROMPTS_DIR = Path(__file__).parent / "prompts"


class OpenAIProvider(LLMProvider):
    code = "openai"
    is_mock = False

    def __init__(self, api_key: str, model: str, timeout: float = 60.0):
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)

    def _load_prompt(self, prompt_version: str) -> str:
        path = _PROMPTS_DIR / f"{prompt_version}.md"
        if not path.exists():
            raise LLMProviderError(f"unknown prompt version {prompt_version}")
        return path.read_text(encoding="utf-8")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def analyze_company(
        self, context: StructuredAnalysisContext, prompt_version: str
    ) -> LLMAnalysisResult:
        template = self._load_prompt(prompt_version)
        context_json = context.model_dump_json(indent=2)
        prompt = template.replace("{context_json}", context_json)

        try:
            completion = await self._client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a disciplined financial research assistant."},
                    {"role": "user", "content": prompt},
                ],
                response_format=LLMAnalysisResult,
                temperature=0.2,
            )
        except Exception as exc:  # openai SDK raises various typed exceptions
            raise LLMProviderError(f"OpenAI request failed: {exc}") from exc

        message = completion.choices[0].message
        if message.refusal:
            raise LLMProviderError(f"model refused: {message.refusal}")
        parsed = message.parsed
        if parsed is None:
            raise LLMProviderError("model did not return a parsed structured response")
        return parsed
