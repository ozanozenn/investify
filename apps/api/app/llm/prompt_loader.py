from __future__ import annotations

from pathlib import Path

from app.llm.base import LLMProviderError

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt_template(prompt_version: str) -> str:
    path = _PROMPTS_DIR / f"{prompt_version}.md"
    if not path.exists():
        raise LLMProviderError(f"unknown prompt version {prompt_version}")
    return path.read_text(encoding="utf-8")
