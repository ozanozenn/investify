from __future__ import annotations

from pathlib import Path

from app.llm.base import LLMProviderError
from app.llm.context_formatter import render_context_json
from app.schemas.context import StructuredAnalysisContext

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt_template(prompt_version: str) -> str:
    path = _PROMPTS_DIR / f"{prompt_version}.md"
    if not path.exists():
        raise LLMProviderError(f"unknown prompt version {prompt_version}")
    return path.read_text(encoding="utf-8")


def render_prompt(
    prompt_version: str,
    context: StructuredAnalysisContext,
    extra_instructions: str | None = None,
) -> str:
    """The full user prompt both real providers send: the versioned
    template with the formatted context embedded, plus — only on the
    hallucination-correction retry — a corrective note appended last so it
    is the most recent instruction the model reads."""
    prompt = load_prompt_template(prompt_version).replace("{context_json}", render_context_json(context))
    if extra_instructions:
        prompt = f"{prompt}\n\n{extra_instructions.strip()}\n"
    return prompt
