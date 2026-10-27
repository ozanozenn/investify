"""Tek seferlik halüsinasyon düzeltme denemesi (ADR-003,
services/llm_analysis.py) — gerçek LLM yerine senaryolu sahte sağlayıcı."""

from __future__ import annotations

import datetime as dt

import pytest

from app.llm.base import LLMProvider, LLMProviderError
from app.schemas.context import CompanyContext, DataQuality, MarketContext, StructuredAnalysisContext
from app.schemas.financial import FinancialMetrics
from app.schemas.llm_analysis import HorizonOutlook, LLMAnalysisResult
from app.schemas.scoring import CategoryScore, ScoreResult
from app.schemas.valuation import ValuationMetrics
from app.services.llm_analysis import analyze_with_hallucination_retry

CLEAN = "Şirketin genel skoru 57,5/100 seviyesinde."
ONE_BAD = "Net kâr marjı 42,7 seviyesinde."
TWO_BAD = "Net kâr marjı 42,7, büyüme %88,8."


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
            overall=57.5,
            overall_weights={},
            engine_version="v1",
        ),
        macro=[],
        disclosures=[],
        data_quality=DataQuality(completeness=1.0, freshness=1.0, metric_coverage=1.0, overall=1.0),
        sources=[],
    )


def _result(summary: str) -> LLMAnalysisResult:
    horizon = HorizonOutlook(outlook="NEUTRAL", rationale="Gerekçe.")
    return LLMAnalysisResult(
        executive_summary=summary,
        what_matters_now=[],
        short_term=horizon,
        medium_term=horizon,
        long_term=horizon,
        bull_case=[],
        bear_case=[],
        key_risks=[],
        key_catalysts=[],
        thesis_breakers=[],
        what_to_watch=[],
    )


class ScriptedLLM(LLMProvider):
    """Her çağrıda sıradaki özeti döndürür (str) ya da hatayı fırlatır."""

    code = "scripted"
    model = "scripted-v1"

    def __init__(self, *script: str | Exception):
        self.script = list(script)
        self.extra_instructions_seen: list[str | None] = []

    async def analyze_company(self, context, prompt_version, extra_instructions=None):
        self.extra_instructions_seen.append(extra_instructions)
        step = self.script[len(self.extra_instructions_seen) - 1]
        if isinstance(step, Exception):
            raise step
        return _result(step)


@pytest.mark.asyncio
async def test_clean_first_answer_does_not_retry():
    llm = ScriptedLLM(CLEAN)
    guarded = await analyze_with_hallucination_retry(llm, _context(), "company-analysis-v4")
    assert llm.extra_instructions_seen == [None]
    assert guarded.meta() == {
        "hallucination_flags": [],
        "hallucination_retry": False,
        "hallucination_flags_first_attempt": [],
    }


@pytest.mark.asyncio
async def test_flagged_first_answer_retries_once_with_correction_and_keeps_clean_one():
    llm = ScriptedLLM(ONE_BAD, CLEAN)
    guarded = await analyze_with_hallucination_retry(llm, _context(), "company-analysis-v4")

    assert len(llm.extra_instructions_seen) == 2
    assert llm.extra_instructions_seen[0] is None
    assert "«42,7»" in llm.extra_instructions_seen[1]
    assert guarded.result.executive_summary == CLEAN
    meta = guarded.meta()
    assert meta["hallucination_flags"] == []
    assert meta["hallucination_retry"] is True
    assert len(meta["hallucination_flags_first_attempt"]) == 1
    assert "42,7" in meta["hallucination_flags_first_attempt"][0]


@pytest.mark.asyncio
async def test_retry_with_more_flags_keeps_first_answer():
    llm = ScriptedLLM(ONE_BAD, TWO_BAD)
    guarded = await analyze_with_hallucination_retry(llm, _context(), "company-analysis-v4")
    assert guarded.result.executive_summary == ONE_BAD
    assert guarded.hallucination_retry is True
    assert guarded.hallucination_flags == guarded.hallucination_flags_first_attempt
    assert len(guarded.hallucination_flags) == 1


@pytest.mark.asyncio
async def test_retry_with_fewer_but_nonzero_flags_keeps_retry():
    llm = ScriptedLLM(TWO_BAD, ONE_BAD)
    guarded = await analyze_with_hallucination_retry(llm, _context(), "company-analysis-v4")
    assert guarded.result.executive_summary == ONE_BAD
    assert len(guarded.hallucination_flags) == 1
    assert len(guarded.hallucination_flags_first_attempt) == 2


@pytest.mark.asyncio
async def test_failed_retry_call_keeps_first_answer_and_records_error():
    llm = ScriptedLLM(ONE_BAD, LLMProviderError("rate limited"))
    guarded = await analyze_with_hallucination_retry(llm, _context(), "company-analysis-v4")
    assert guarded.result.executive_summary == ONE_BAD
    meta = guarded.meta()
    assert meta["hallucination_retry"] is True
    assert len(meta["hallucination_flags"]) == 1
    assert meta["hallucination_retry_error"] == "rate limited"


@pytest.mark.asyncio
async def test_first_call_failure_still_propagates():
    llm = ScriptedLLM(LLMProviderError("down"))
    with pytest.raises(LLMProviderError, match="down"):
        await analyze_with_hallucination_retry(llm, _context(), "company-analysis-v4")
