"""Google Gemini LLM provider — a free-tier alternative to OpenAI for
development (see docs/DATA_SOURCES.md). Implements the same
`LLMProvider` contract (ADR-003: interpretation-only, structured JSON in
→ structured JSON out, Pydantic-validated) as `OpenAIProvider`; the two
are interchangeable from `services/refresh_pipeline.py`'s point of view.

Unlike `OpenAIProvider`, this does not rely on the SDK's own `.parsed`
convenience (not present across all google-genai SDK versions) — the raw
`response.text` is always explicitly validated against `LLMAnalysisResult`
via Pydantic, so a malformed response fails loudly (`LLMProviderError`,
pipeline stage marked FAILED) rather than being silently accepted.
"""

from __future__ import annotations

from google import genai
from google.genai import types
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.llm.base import LLMProvider, LLMProviderError
from app.llm.prompt_loader import load_prompt_template
from app.schemas.context import StructuredAnalysisContext
from app.schemas.llm_analysis import LLMAnalysisResult

logger = get_logger(__name__)

_SYSTEM_INSTRUCTION = "You are a disciplined financial research assistant."


class GeminiProvider(LLMProvider):
    code = "gemini"
    is_mock = False

    def __init__(self, api_key: str, model: str, timeout: float = 60.0):
        self.model = model
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout * 1000))
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def analyze_company(
        self, context: StructuredAnalysisContext, prompt_version: str
    ) -> LLMAnalysisResult:
        template = load_prompt_template(prompt_version)
        context_json = context.model_dump_json(indent=2)
        prompt = template.replace("{context_json}", context_json)

        try:
            response = await self._client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=LLMAnalysisResult,
                    temperature=0.2,
                ),
            )
        except Exception as exc:  # google-genai raises various typed exceptions
            raise LLMProviderError(f"Gemini request failed: {exc}") from exc

        if not response.text:
            raise LLMProviderError("Gemini returned an empty response (possibly blocked by safety filters)")

        try:
            return LLMAnalysisResult.model_validate_json(response.text)
        except ValidationError as exc:
            raise LLMProviderError(f"Gemini response did not match LLMAnalysisResult schema: {exc}") from exc
