"""Refresh pipeline'ın uçtan uca halüsinasyon düzeltme denemesi (ADR-003):
ilk LLM yanıtı context'te olmayan bir sayı içerir, ikincisi temizdir →
tek düzeltme denemesi yapılır, temiz yanıt saklanır, `_meta` kaydedilir."""

from __future__ import annotations

import pytest

from app.llm.base import LLMProvider
from app.schemas.llm_analysis import HorizonOutlook, LLMAnalysisResult

_UNSUPPORTED = "Şirketin net kâr marjı 987.654,3 seviyesine ulaştı."
_CLEAN = "Şirketin görünümü hükümle uyumlu."


def _result(summary: str) -> LLMAnalysisResult:
    horizon = HorizonOutlook(outlook="NEUTRAL", rationale="Gerekçe.")
    return LLMAnalysisResult(
        executive_summary=summary,
        what_matters_now=["Tek önemli madde."],
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


class FlakyThenCleanLLM(LLMProvider):
    code = "flaky"
    model = "flaky-v1"
    is_mock = False

    def __init__(self):
        self.calls: list[str | None] = []

    async def analyze_company(self, context, prompt_version, extra_instructions=None):
        self.calls.append(extra_instructions)
        return _result(_UNSUPPORTED if len(self.calls) == 1 else _CLEAN)


@pytest.mark.asyncio
async def test_refresh_retries_once_and_persists_clean_answer_with_meta(client, fake_providers):
    llm = FlakyThenCleanLLM()
    fake_providers.llm = llm

    resp = await client.post("/api/companies/TEST/refresh")
    assert resp.status_code == 200

    assert len(llm.calls) == 2
    assert llm.calls[0] is None
    assert "987.654,3" in llm.calls[1]

    # Persisted snapshot (GET reads it back), not just the refresh response.
    analysis = (await client.get("/api/companies/TEST/analysis")).json()["analysis"]
    assert analysis["executive_summary"] == _CLEAN
    assert analysis["what_matters_now"] == ["Tek önemli madde."]
    meta = analysis["_meta"]
    assert meta["hallucination_flags"] == []
    assert meta["hallucination_retry"] is True
    assert len(meta["hallucination_flags_first_attempt"]) == 1
    assert "987.654,3" in meta["hallucination_flags_first_attempt"][0]
    assert meta["prompt_version"] == "company-analysis-v4"


@pytest.mark.asyncio
async def test_mock_refresh_records_no_retry(client):
    resp = await client.post("/api/companies/TEST/refresh")
    meta = resp.json()["analysis"]["_meta"]
    assert meta["hallucination_retry"] is False
    assert meta["hallucination_flags"] == []
    assert meta["hallucination_flags_first_attempt"] == []
