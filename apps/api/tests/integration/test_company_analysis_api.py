import pytest


@pytest.mark.asyncio
async def test_refresh_then_get_analysis_roundtrip(client):
    refresh_resp = await client.post("/api/companies/TEST/refresh")
    assert refresh_resp.status_code == 200
    body = refresh_resp.json()

    assert body["ticker"] == "TEST"
    assert body["company"]["name"] == "TEST Test A.Ş."
    assert body["stage_results"]["market"] == "SUCCESS"
    assert body["stage_results"]["financials"] == "SUCCESS"
    assert 0 <= body["scores"]["overall"] <= 100
    assert body["analysis"]["_meta"]["llm_is_mocked"] is True
    assert body["data_quality"]["overall"] > 0
    assert body["versions"]["financial_engine"] == "v1"

    # GET should return the persisted snapshot without re-running providers
    # (no stage_results on a cache read — only present right after a refresh).
    get_resp = await client.get("/api/companies/TEST/analysis")
    assert get_resp.status_code == 200
    cached = get_resp.json()
    assert cached["stage_results"] is None
    assert cached["scores"]["overall"] == body["scores"]["overall"]


@pytest.mark.asyncio
async def test_first_time_get_triggers_implicit_refresh(client):
    # No prior refresh call — GET alone should bootstrap + compute everything.
    resp = await client.get("/api/companies/NEWCO/analysis")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "NEWCO"
    assert body["metrics"]["revenue_growth_yoy"] is not None


@pytest.mark.asyncio
async def test_partial_failure_does_not_crash_pipeline(client, fake_providers):
    fake_providers.financial.fail = True  # simulate a dead provider (section 37)

    resp = await client.post("/api/companies/BROKEN/refresh")
    assert resp.status_code == 200
    body = resp.json()

    assert body["stage_results"]["financials"] == "FAILED"
    assert body["stage_results"]["market"] == "SUCCESS"
    assert "Finansal tablo verisi alınamadı" in body["data_quality"]["warnings"]
    # No financial data at all -> scoring degrades but does not error.
    assert body["metrics"]["as_of_period"] == "N/A"


@pytest.mark.asyncio
async def test_analysis_history_lists_snapshots(client):
    await client.post("/api/companies/TEST/refresh")
    await client.post("/api/companies/TEST/refresh")

    resp = await client.get("/api/companies/TEST/analysis/history")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 2
    assert all("overall_score" in row for row in history)


@pytest.mark.asyncio
async def test_search_returns_static_index_matches(client):
    resp = await client.get("/api/companies/search", params={"q": "THY"})
    assert resp.status_code == 200
    results = resp.json()
    assert any(r["ticker"] == "THYAO" for r in results)


@pytest.mark.asyncio
async def test_health_check_does_not_require_auth(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
