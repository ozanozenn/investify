"""GeminiProvider has no live network test (no real GEMINI_API_KEY in this
environment — same reason OpenAIProvider has no network-mocked test
either). This covers the one thing that IS ours to get right: parsing and
validating the raw response text against LLMAnalysisResult, and wrapping
every failure mode as LLMProviderError rather than crashing the pipeline
or silently accepting a malformed result (ADR-003)."""

from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock

import pytest

from app.llm.base import LLMProviderError
from app.llm.gemini_provider import GeminiProvider
from app.schemas.context import CompanyContext, DataQuality, MarketContext, StructuredAnalysisContext
from app.schemas.financial import FinancialMetrics
from app.schemas.scoring import CategoryScore, ScoreResult
from app.schemas.valuation import ValuationMetrics


def _context() -> StructuredAnalysisContext:
    empty_category = CategoryScore(label="x", score=50.0, components=[])
    return StructuredAnalysisContext(
        ticker="TEST",
        as_of=dt.datetime.now(dt.timezone.utc),
        company=CompanyContext(ticker="TEST", name="Test A.Ş.", sector=None, industry=None),
        market=MarketContext(price=10.0, currency="TRY", market_cap=1000.0, as_of=None),
        metrics=FinancialMetrics(as_of_period="2025"),
        financial_history=[],
        valuation=ValuationMetrics(),
        scores=ScoreResult(
            growth=empty_category,
            profitability=empty_category,
            balance_sheet=empty_category,
            cash_flow=empty_category,
            valuation=empty_category,
            overall=50.0,
            overall_weights={},
            engine_version="v1",
        ),
        macro=[],
        disclosures=[],
        data_quality=DataQuality(completeness=1.0, freshness=1.0, metric_coverage=1.0, overall=1.0),
        sources=[],
    )


_V4_JSON = """{
    "executive_summary": "Test summary.",
    "what_matters_now": ["Önemli tek şey."],
    "short_term": {"outlook": "NEUTRAL", "rationale": "Kısa vade gerekçesi."},
    "medium_term": {"outlook": "NEUTRAL", "rationale": "Orta vade gerekçesi."},
    "long_term": {"outlook": "NEUTRAL", "rationale": "Uzun vade gerekçesi."},
    "bull_case": [], "bear_case": [], "key_risks": [], "key_catalysts": [],
    "thesis_breakers": [], "what_to_watch": []
}"""


def _provider_with_response(text: str | None) -> GeminiProvider:
    provider = GeminiProvider(api_key="test-key", model="gemini-3.6-flash")
    fake_response = type("FakeResponse", (), {"text": text})()
    provider._client.aio.models.generate_content = AsyncMock(return_value=fake_response)
    return provider


@pytest.mark.asyncio
async def test_valid_json_response_parses_into_llm_analysis_result():
    provider = _provider_with_response(_V4_JSON)
    result = await provider.analyze_company(_context(), "company-analysis-v4")
    assert result.executive_summary == "Test summary."
    assert result.what_matters_now == ["Önemli tek şey."]
    assert result.short_term.outlook == "NEUTRAL"
    assert result.short_term.rationale == "Kısa vade gerekçesi."


@pytest.mark.asyncio
async def test_extra_instructions_are_appended_to_the_prompt():
    provider = _provider_with_response(_V4_JSON)
    await provider.analyze_company(_context(), "company-analysis-v4", extra_instructions="## Düzeltme talebi\nX")
    sent_prompt = provider._client.aio.models.generate_content.call_args.kwargs["contents"]
    assert sent_prompt.rstrip().endswith("## Düzeltme talebi\nX")
    assert '"ticker": "TEST"' in sent_prompt  # context still embedded before it


@pytest.mark.asyncio
async def test_pre_v4_shaped_response_is_rejected():
    # v1-v3 horizon shape (confidence/drivers, no rationale) no longer
    # matches the output contract — must fail loudly, not half-parse.
    old_shape = _V4_JSON.replace(
        '{"outlook": "NEUTRAL", "rationale": "Kısa vade gerekçesi."}',
        '{"outlook": "NEUTRAL", "confidence": 0.5, "drivers": [], "risks": [], "catalysts": []}',
    )
    provider = _provider_with_response(old_shape)
    with pytest.raises(LLMProviderError, match="did not match"):
        await provider.analyze_company(_context(), "company-analysis-v4")


@pytest.mark.asyncio
async def test_empty_response_raises_llm_provider_error():
    provider = _provider_with_response(None)
    with pytest.raises(LLMProviderError, match="empty response"):
        await provider.analyze_company(_context(), "company-analysis-v1")


@pytest.mark.asyncio
async def test_malformed_json_raises_llm_provider_error_not_generic_exception():
    provider = _provider_with_response("{not valid json")
    with pytest.raises(LLMProviderError):
        await provider.analyze_company(_context(), "company-analysis-v1")


@pytest.mark.asyncio
async def test_schema_mismatch_raises_llm_provider_error():
    # Valid JSON, but missing every required field.
    provider = _provider_with_response("{}")
    with pytest.raises(LLMProviderError, match="did not match"):
        await provider.analyze_company(_context(), "company-analysis-v1")


@pytest.mark.asyncio
async def test_sdk_exception_is_wrapped_as_llm_provider_error():
    provider = GeminiProvider(api_key="test-key", model="gemini-3.6-flash")
    provider._client.aio.models.generate_content = AsyncMock(side_effect=RuntimeError("network down"))
    with pytest.raises(LLMProviderError, match="Gemini request failed"):
        await provider.analyze_company(_context(), "company-analysis-v1")
