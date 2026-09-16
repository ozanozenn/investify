from __future__ import annotations

import datetime as dt

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.company import Company, Industry, Sector, Ticker
from app.models.snapshots import AnalysisSnapshot
from app.services.peer_comparison import compute_peer_comparison

# Replicates the async in-memory SQLite fixture pattern from
# tests/integration/conftest.py's `db_session` (not imported from there
# since this slice must not touch any existing tracked file).


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


async def _make_company(
    session: AsyncSession,
    name: str,
    ticker: str,
    industry: Industry | None,
    is_financial_industry: bool = False,
) -> Company:
    company = Company(
        name=name,
        industry_id=industry.id if industry is not None else None,
        is_financial_industry=is_financial_industry,
    )
    session.add(company)
    await session.flush()
    session.add(Ticker(company_id=company.id, symbol=ticker, exchange="BIST", is_primary=True))
    await session.flush()
    return company


async def _make_snapshot(
    session: AsyncSession,
    company: Company,
    ticker: str,
    overall_score: float | None,
    pe: float | None,
    pb: float | None,
    ev_ebitda: float | None,
    created_at: dt.datetime | None = None,
) -> AnalysisSnapshot:
    now = created_at or _now()
    snapshot = AnalysisSnapshot(
        company_id=company.id,
        ticker=ticker,
        as_of=now,
        financial_engine_version="v1",
        scoring_engine_version="v1",
        valuation_engine_version="v1",
        prompt_version="v1",
        llm_model="mock",
        llm_is_mocked=True,
        context_json={
            "scores": {"overall": overall_score},
            "valuation": {"pe": pe, "pb": pb, "ev_ebitda": ev_ebitda},
        },
        analysis_json={},
        data_quality_json={},
        created_at=now,
    )
    session.add(snapshot)
    await session.flush()
    return snapshot


async def _make_sector_and_industries(session: AsyncSession, sector_name: str, *industry_names: str):
    sector = Sector(name=sector_name)
    session.add(sector)
    await session.flush()
    industries = []
    for name in industry_names:
        industry = Industry(sector_id=sector.id, name=name)
        session.add(industry)
        await session.flush()
        industries.append(industry)
    return sector, industries


@pytest.mark.asyncio
async def test_no_peers_returns_insufficient_without_crashing(db_session: AsyncSession):
    sector, (industry,) = await _make_sector_and_industries(db_session, "Sanayi", "Otomotiv")
    subject = await _make_company(db_session, "Solo A.S.", "SOLO", industry)
    await _make_snapshot(db_session, subject, "SOLO", overall_score=70.0, pe=10.0, pb=1.5, ev_ebitda=8.0)
    await db_session.commit()

    result = await compute_peer_comparison(db_session, "SOLO")

    assert result.peer_group_basis == "none"
    assert result.peer_count == 0
    assert result.peers == []
    assert result.insufficient_peers is True
    assert result.insufficient_peers_reason == "no_other_companies_refreshed_in_industry_or_sector"
    assert result.median_overall_score is None
    assert result.median_pe is None
    assert result.median_pb is None
    assert result.median_ev_ebitda is None
    assert result.overall_score_vs_median is None
    assert result.this_company.overall_score == 70.0


@pytest.mark.asyncio
async def test_two_industry_peers_compute_median(db_session: AsyncSession):
    sector, (industry,) = await _make_sector_and_industries(db_session, "Sanayi", "Otomotiv")

    subject = await _make_company(db_session, "Subject A.S.", "SUBJ", industry)
    await _make_snapshot(db_session, subject, "SUBJ", overall_score=70.0, pe=10.0, pb=1.5, ev_ebitda=8.0)

    peer1 = await _make_company(db_session, "Peer One A.S.", "PEER1", industry)
    await _make_snapshot(db_session, peer1, "PEER1", overall_score=60.0, pe=8.0, pb=1.2, ev_ebitda=6.0)

    peer2 = await _make_company(db_session, "Peer Two A.S.", "PEER2", industry)
    await _make_snapshot(db_session, peer2, "PEER2", overall_score=80.0, pe=12.0, pb=2.0, ev_ebitda=10.0)

    await db_session.commit()

    result = await compute_peer_comparison(db_session, "SUBJ")

    assert result.peer_group_basis == "industry"
    assert result.peer_count == 2
    assert {p.ticker for p in result.peers} == {"PEER1", "PEER2"}
    # median of [60.0, 80.0] = 70.0, of [8.0, 12.0] = 10.0, of [1.2, 2.0] = 1.6, of [6.0, 10.0] = 8.0
    assert result.median_overall_score == pytest.approx(70.0)
    assert result.median_pe == pytest.approx(10.0)
    assert result.median_pb == pytest.approx(1.6)
    assert result.median_ev_ebitda == pytest.approx(8.0)
    assert result.overall_score_vs_median == pytest.approx(0.0)
    assert result.insufficient_peers is False
    assert result.insufficient_peers_reason is None


@pytest.mark.asyncio
async def test_falls_back_to_sector_when_industry_has_no_refreshed_peers(db_session: AsyncSession):
    sector, (industry_a, industry_b) = await _make_sector_and_industries(
        db_session, "Sanayi", "Otomotiv", "Cimento"
    )

    subject = await _make_company(db_session, "Subject A.S.", "SUBJ", industry_a)
    await _make_snapshot(db_session, subject, "SUBJ", overall_score=70.0, pe=10.0, pb=1.5, ev_ebitda=8.0)

    # No other refreshed company in industry_a, but one in industry_b (same sector).
    sector_peer = await _make_company(db_session, "Sector Peer A.S.", "SPEER", industry_b)
    await _make_snapshot(db_session, sector_peer, "SPEER", overall_score=50.0, pe=6.0, pb=1.0, ev_ebitda=4.0)

    await db_session.commit()

    result = await compute_peer_comparison(db_session, "SUBJ")

    assert result.peer_group_basis == "sector"
    assert result.peer_count == 1
    assert result.peers[0].ticker == "SPEER"
    assert result.median_overall_score == pytest.approx(50.0)
    assert result.insufficient_peers is False


@pytest.mark.asyncio
async def test_financial_industry_mismatch_excluded(db_session: AsyncSession):
    sector, (industry,) = await _make_sector_and_industries(db_session, "Finans", "Bankacilik")

    subject = await _make_company(
        db_session, "Bank A.S.", "BANKA", industry, is_financial_industry=True
    )
    await _make_snapshot(db_session, subject, "BANKA", overall_score=70.0, pe=10.0, pb=1.5, ev_ebitda=8.0)

    # Same industry, but not flagged as a financial company — must be excluded.
    non_financial_peer = await _make_company(
        db_session, "Not A Bank A.S.", "NOTBNK", industry, is_financial_industry=False
    )
    await _make_snapshot(
        db_session, non_financial_peer, "NOTBNK", overall_score=90.0, pe=20.0, pb=3.0, ev_ebitda=15.0
    )

    await db_session.commit()

    result = await compute_peer_comparison(db_session, "BANKA")

    assert result.peer_group_basis == "none"
    assert result.peer_count == 0
    assert result.insufficient_peers is True


@pytest.mark.asyncio
async def test_company_without_any_snapshot_excluded_from_peer_set(db_session: AsyncSession):
    sector, (industry,) = await _make_sector_and_industries(db_session, "Sanayi", "Otomotiv")

    subject = await _make_company(db_session, "Subject A.S.", "SUBJ", industry)
    await _make_snapshot(db_session, subject, "SUBJ", overall_score=70.0, pe=10.0, pb=1.5, ev_ebitda=8.0)

    # Has a Ticker + Company row, but no AnalysisSnapshot at all.
    await _make_company(db_session, "Never Refreshed A.S.", "NOREF", industry)

    await db_session.commit()

    result = await compute_peer_comparison(db_session, "SUBJ")

    assert result.peer_group_basis == "none"
    assert result.peer_count == 0
    assert result.insufficient_peers is True
    assert all(p.ticker != "NOREF" for p in result.peers)
