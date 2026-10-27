"""İzleme listesi: CRUD, özet içeriği, toplu yenileme işi ve zamanlayıcı (ADR-013).

Toplu iş her hisse için kendi oturumunu açtığından burada conftest'teki tek
bağlantılı in-memory DB yerine geçici bir SQLite dosyası kullanılır.
"""

from __future__ import annotations

import datetime as dt

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db, get_providers, get_session_factory
from app.core.config import Settings, get_settings
from app.lifespan import lifespan
from app.llm.base import LLMProviderError
from app.llm.mock_provider import MockLLMProvider
from app.main import app
from app.models.base import Base
from app.models.company import Ticker
from app.models.snapshots import AnalysisSnapshot
from app.models.watchlist import WatchlistItem
from app.providers.base import ProviderUnavailableError
from app.services import watchlist as watchlist_service
from app.services.watchlist_refresh import refresh_runner, refresh_watchlist
from tests.integration.conftest import FakeCompanyProvider

UTC = dt.timezone.utc


class FailingForTickerLLM(MockLLMProvider):
    """Belirli hisselerde LLM kesintisi taklidi — `run_refresh` hata fırlatır."""

    def __init__(self, failing: set[str]):
        self.failing = failing

    async def analyze_company(self, context, prompt_version):
        if context.ticker in self.failing:
            raise LLMProviderError("simulated LLM outage")
        return await super().analyze_company(context, prompt_version)


class UnknownTickerCompanyProvider(FakeCompanyProvider):
    async def get_company_profile(self, ticker: str) -> dict:
        if ticker == "YOKBOYLE":
            raise ProviderUnavailableError(self.code, "no profile")
        return await super().get_company_profile(ticker)


def _test_settings() -> Settings:
    return Settings(auth_dev_bypass=True, app_env="development")


@pytest_asyncio.fixture
async def wl_session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'watchlist.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    await engine.dispose()


@pytest_asyncio.fixture
async def wl_client(wl_session_factory, fake_providers):
    async def override_get_db():
        async with wl_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_providers] = lambda: fake_providers
    app.dependency_overrides[get_settings] = _test_settings
    app.dependency_overrides[get_session_factory] = lambda: wl_session_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await refresh_runner.wait()
    refresh_runner.last_report = None
    app.dependency_overrides.clear()


async def _add_directly(session_factory, fake_providers, *tickers: str) -> None:
    async with session_factory() as session:
        for ticker in tickers:
            await watchlist_service.add_item(session, ticker, fake_providers.company)


def _snapshot(company_id: int, ticker: str, created_at: dt.datetime, context: dict) -> AnalysisSnapshot:
    return AnalysisSnapshot(
        company_id=company_id,
        ticker=ticker,
        as_of=created_at,
        financial_engine_version="v1",
        scoring_engine_version="v1",
        valuation_engine_version="v1",
        prompt_version="test",
        llm_model="mock-v1",
        llm_is_mocked=True,
        context_json=context,
        analysis_json={},
        data_quality_json={},
        created_at=created_at,
    )


# --- CRUD ---------------------------------------------------------------


async def test_empty_watchlist_reports_scheduler_disabled(wl_client):
    resp = await wl_client.get("/api/watchlist")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["scheduler"]["enabled"] is False
    assert body["scheduler"]["running"] is False
    assert body["scheduler"]["schedule_label"] == "Hafta içi her gün 18:30 (Europe/Istanbul)"


async def test_add_list_remove_roundtrip(wl_client):
    created = await wl_client.post("/api/watchlist", json={"ticker": " thyao "})
    assert created.status_code == 201
    item = created.json()
    assert item["ticker"] == "THYAO"
    assert item["name"] == "THYAO Test A.Ş."
    assert item["has_analysis"] is False
    assert item["verdict"] is None

    again = await wl_client.post("/api/watchlist", json={"ticker": "THYAO"})
    assert again.status_code == 200  # idempotent

    items = (await wl_client.get("/api/watchlist")).json()["items"]
    assert [i["ticker"] for i in items] == ["THYAO"]

    assert (await wl_client.delete("/api/watchlist/thyao")).status_code == 204
    assert (await wl_client.get("/api/watchlist")).json()["items"] == []

    missing = await wl_client.delete("/api/watchlist/THYAO")
    assert missing.status_code == 404
    assert "izleme listende yok" in missing.json()["detail"]


async def test_add_rejects_malformed_ticker(wl_client):
    resp = await wl_client.post("/api/watchlist", json={"ticker": "TH Y!"})
    assert resp.status_code == 422
    assert "Geçersiz hisse kodu" in resp.json()["detail"]


async def test_add_unknown_ticker_is_validated_like_company_routes(wl_client, fake_providers, wl_session_factory):
    fake_providers.company = UnknownTickerCompanyProvider()
    resp = await wl_client.post("/api/watchlist", json={"ticker": "YOKBOYLE"})
    assert resp.status_code == 404
    assert "YOKBOYLE kodlu şirket bulunamadı" in resp.json()["detail"]

    async with wl_session_factory() as session:
        assert (await session.execute(select(Ticker).where(Ticker.symbol == "YOKBOYLE"))).first() is None
    assert (await wl_client.get("/api/watchlist")).json()["items"] == []


# --- Özet ----------------------------------------------------------------


def _context(name: str, price: float, overall: float, verdict: dict | None, unsupported: str | None = None) -> dict:
    return {
        "company": {"name": name},
        "market": {"price": price, "currency": "TRY"},
        "scores": {"overall": overall, "unsupported_reason": unsupported},
        "unsupported_reason": unsupported,
        "verdict": verdict,
    }


_VERDICT = {
    "price": "UCUZ",
    "quality": "GUCLU",
    "confidence": "YUKSEK",
    "signal": "AL",
    "signal_is_demo": True,
    "headline": "Ucuz ve güçlü görünüyor.",
    "lenses": [],
    "agreement": 1.0,
    "overall_score": 61.5,
    "engine_version": "v1",
    "missing_fields": [],
    "unsupported_reason": None,
}


async def test_summary_uses_latest_snapshot_and_computes_score_change(wl_client, wl_session_factory):
    await wl_client.post("/api/watchlist", json={"ticker": "SUMRY"})
    older = dt.datetime(2026, 10, 20, 15, 30, tzinfo=UTC)
    newer = dt.datetime(2026, 10, 21, 15, 30, tzinfo=UTC)
    async with wl_session_factory() as session:
        company_id = (await session.execute(select(Ticker.company_id).where(Ticker.symbol == "SUMRY"))).scalar_one()
        session.add(_snapshot(company_id, "SUMRY", older, _context("Özet A.Ş.", 40.0, 55.0, None)))
        session.add(_snapshot(company_id, "SUMRY", newer, _context("Özet A.Ş.", 42.5, 61.5, _VERDICT)))
        await session.commit()

    item = (await wl_client.get("/api/watchlist")).json()["items"][0]
    assert item["has_analysis"] is True
    assert item["name"] == "Özet A.Ş."
    assert item["price"] == 42.5
    assert item["currency"] == "TRY"
    assert item["overall_score"] == 61.5
    assert item["previous_overall_score"] == 55.0
    assert item["score_change"] == 6.5
    assert item["verdict"] == {
        "price": "UCUZ",
        "quality": "GUCLU",
        "confidence": "YUKSEK",
        "signal": "AL",
        "signal_is_demo": True,
        "headline": "Ucuz ve güçlü görünüyor.",
        "unsupported_reason": None,
    }
    assert dt.datetime.fromisoformat(item["last_refreshed_at"]).replace(tzinfo=UTC) == newer
    assert item["last_job_status"] is None
    assert item["last_job_failed"] is False


async def test_summary_has_no_score_for_unsupported_industry(wl_client, wl_session_factory):
    await wl_client.post("/api/watchlist", json={"ticker": "BANKA"})
    async with wl_session_factory() as session:
        company_id = (await session.execute(select(Ticker.company_id).where(Ticker.symbol == "BANKA"))).scalar_one()
        session.add(_snapshot(company_id, "BANKA", dt.datetime(2026, 10, 20, tzinfo=UTC), _context("B", 10.0, 50.0, None)))
        session.add(
            _snapshot(company_id, "BANKA", dt.datetime(2026, 10, 21, tzinfo=UTC), _context("B", 11.0, 0.0, None, "Desteklenmiyor"))
        )
        await session.commit()

    item = (await wl_client.get("/api/watchlist")).json()["items"][0]
    assert item["overall_score"] is None  # 0 puan yanıltıcı olurdu
    assert item["previous_overall_score"] == 50.0
    assert item["score_change"] is None


async def test_summary_after_real_refresh_contains_deterministic_verdict(wl_client):
    analysis = (await wl_client.post("/api/companies/VRDWL/refresh")).json()
    item = (await wl_client.post("/api/watchlist", json={"ticker": "VRDWL"})).json()

    assert item["has_analysis"] is True
    assert item["overall_score"] == analysis["scores"]["overall"]
    assert item["price"] == analysis["market"]["price"]
    assert item["verdict"]["confidence"] == analysis["verdict"]["confidence"]
    assert item["verdict"]["headline"] == analysis["verdict"]["headline"]
    assert item["score_change"] is None  # tek snapshot var


# --- Toplu yenileme işi -------------------------------------------------------


async def test_refresh_job_refreshes_all_and_survives_failing_ticker(wl_client, wl_session_factory, fake_providers):
    await _add_directly(wl_session_factory, fake_providers, "AAAA", "BOZUK", "CCCC")
    fake_providers.llm = FailingForTickerLLM({"BOZUK"})

    report = await refresh_watchlist(wl_session_factory, fake_providers, _test_settings(), trigger="scheduled")

    assert [(o.ticker, o.status) for o in report.outcomes] == [
        ("AAAA", "SUCCESS"),
        ("BOZUK", "FAILED"),
        ("CCCC", "SUCCESS"),
    ]
    assert report.succeeded == 2 and report.failed == 1
    assert "simulated LLM outage" in report.outcomes[1].error

    async with wl_session_factory() as session:
        snap_tickers = (await session.execute(select(AnalysisSnapshot.ticker))).scalars().all()
        rows = {r.ticker: r for r in (await session.execute(select(WatchlistItem))).scalars().all()}
    assert sorted(snap_tickers) == ["AAAA", "CCCC"]
    assert rows["BOZUK"].last_refresh_status == "FAILED"
    assert rows["AAAA"].last_refresh_status == "SUCCESS"
    assert all(r.last_refresh_trigger == "scheduled" and r.last_refresh_at is not None for r in rows.values())

    items = {i["ticker"]: i for i in (await wl_client.get("/api/watchlist")).json()["items"]}
    assert items["BOZUK"]["last_job_failed"] is True
    assert "simulated LLM outage" in items["BOZUK"]["last_job_error"]
    assert items["BOZUK"]["has_analysis"] is False
    assert items["AAAA"]["last_job_failed"] is False
    assert items["AAAA"]["has_analysis"] is True
    assert items["AAAA"]["verdict"] is not None


async def test_refresh_job_skips_tickers_already_done_in_same_slot(wl_session_factory, fake_providers):
    await _add_directly(wl_session_factory, fake_providers, "SLOTA", "SLOTB")
    slot = dt.datetime.now(UTC)
    first = await refresh_watchlist(
        wl_session_factory, fake_providers, _test_settings(), trigger="scheduled", not_refreshed_since=slot
    )
    assert len(first.outcomes) == 2 and first.skipped == []

    # İkinci bir worker aynı dilimi yakalarsa iş tekrarlanmaz.
    duplicate = await refresh_watchlist(
        wl_session_factory, fake_providers, _test_settings(), trigger="scheduled", not_refreshed_since=slot
    )
    assert duplicate.outcomes == [] and duplicate.skipped == ["SLOTA", "SLOTB"]

    later = await refresh_watchlist(
        wl_session_factory, fake_providers, _test_settings(), trigger="scheduled",
        not_refreshed_since=dt.datetime.now(UTC),
    )
    assert len(later.outcomes) == 2


# --- Elle tetikleme ---------------------------------------------------------


async def test_manual_refresh_runs_job_in_background(wl_client):
    await wl_client.post("/api/watchlist", json={"ticker": "MANA"})
    await wl_client.post("/api/watchlist", json={"ticker": "MANB"})

    resp = await wl_client.post("/api/watchlist/refresh")
    assert resp.status_code == 202
    assert resp.json()["started"] is True
    assert resp.json()["tickers"] == 2

    await refresh_runner.wait()
    body = (await wl_client.get("/api/watchlist")).json()
    assert body["scheduler"]["running"] is False
    assert body["scheduler"]["last_run_trigger"] == "manual"
    assert body["scheduler"]["last_run_succeeded"] == 2
    assert body["scheduler"]["last_run_failed"] == 0
    for item in body["items"]:
        assert item["has_analysis"] is True
        assert item["last_job_trigger"] == "manual"
        assert item["last_job_status"] == "SUCCESS"


async def test_manual_refresh_rejected_while_running(wl_client):
    await wl_client.post("/api/watchlist", json={"ticker": "BUSY"})
    async with refresh_runner._lock:  # başka bir çalıştırma sürüyor
        resp = await wl_client.post("/api/watchlist/refresh")
        assert (await wl_client.get("/api/watchlist")).json()["scheduler"]["running"] is True
    assert resp.status_code == 409
    assert resp.json()["detail"] == "İzleme listesi yenilemesi zaten çalışıyor."


async def test_manual_refresh_with_empty_list_is_rejected(wl_client):
    resp = await wl_client.post("/api/watchlist/refresh")
    assert resp.status_code == 400
    assert "boş" in resp.json()["detail"]


# --- Lifespan / zamanlayıcı ----------------------------------------------


async def test_lifespan_does_not_start_scheduler_in_tests():
    async with lifespan(app):
        assert app.state.watchlist_scheduler is None
    assert app.state.watchlist_scheduler is None


async def test_lifespan_starts_and_stops_scheduler_when_enabled(monkeypatch):
    enabled = Settings(auth_dev_bypass=True, app_env="development", watchlist_refresh_enabled=True)
    monkeypatch.setattr("app.lifespan.get_settings", lambda: enabled)

    async with lifespan(app):
        scheduler = app.state.watchlist_scheduler
        assert scheduler is not None and scheduler.is_running
        assert scheduler.next_run_at is not None and scheduler.next_run_at > dt.datetime.now(UTC)
    assert not scheduler.is_running
    assert app.state.watchlist_scheduler is None


@pytest.mark.parametrize("raw", ["THYAO", "thyao", " Asels "])
def test_normalize_ticker_accepts_bist_codes(raw):
    assert watchlist_service.normalize_ticker(raw) == raw.strip().upper()
