from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    timezone: str = Field(default="Europe/Istanbul")

    # --- Database ---
    database_url: str = Field(
        default="postgresql+asyncpg://investify:investify@localhost:55433/investify"
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg2://investify:investify@localhost:55433/investify"
    )

    # --- Redis (cache only in Phase 1) ---
    redis_url: str = Field(default="redis://localhost:63790/0")
    cache_enabled: bool = Field(default=True)

    # --- Auth ---
    auth_dev_bypass: bool = Field(default=True)
    jwt_secret: str = Field(default="dev-only-insecure-secret-change-me")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=60 * 24 * 7)
    app_user_email: str = Field(default="ozanozen4@gmail.com")
    app_user_password: str = Field(default="changeme")

    # --- Providers ---
    evds_api_key: str | None = Field(default=None)
    request_timeout_seconds: float = Field(default=15.0)

    # --- LLM ---
    # Provider selection is automatic from which key is set (see
    # services/provider_bundle.py): OpenAI takes priority if configured
    # (the production/paid path), otherwise Gemini (a free-tier dev
    # alternative — see docs/DATA_SOURCES.md), otherwise MockLLMProvider.
    openai_api_key: str | None = Field(default=None)
    openai_model: str = Field(default="gpt-4.1-mini")
    gemini_api_key: str | None = Field(default=None)
    gemini_model: str = Field(default="gemini-3.6-flash")
    llm_prompt_version: str = Field(default="company-analysis-v3")

    # --- Versions (section 79) ---
    financial_engine_version: str = Field(default="v1")
    scoring_engine_version: str = Field(default="v1")
    valuation_engine_version: str = Field(default="v1")

    # --- CORS ---
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @property
    def is_llm_mocked(self) -> bool:
        return not (self.openai_api_key or self.gemini_api_key)

    @property
    def is_evds_mocked(self) -> bool:
        return not self.evds_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_scoring_config() -> dict:
    with open(CONFIG_DIR / "scoring.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def get_analysis_config() -> dict:
    with open(CONFIG_DIR / "analysis.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def get_tcmb_calendar_config() -> dict:
    with open(CONFIG_DIR / "tcmb_calendar.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def get_verdict_config() -> dict:
    with open(CONFIG_DIR / "verdict.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)
