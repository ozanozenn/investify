"""Bankalar yalnızca bankalarla karşılaştırılır (ADR-014)."""

from __future__ import annotations

import datetime as dt

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.company import Company, Industry, Sector, Ticker
from app.models.snapshots import AnalysisSnapshot
from app.services.peer_comparison import compute_peer_comparison, peer_medians_for_company


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


async def _company(session: AsyncSession, ticker: str, industry: Industry, pb: float | None) -> Company:
    company = Company(name=f"{ticker} A.Ş.", industry_id=industry.id, is_financial_industry=True)
    session.add(company)
    await session.flush()
    session.add(Ticker(company_id=company.id, symbol=ticker, exchange="BIST", is_primary=True))
    now = dt.datetime.now(dt.timezone.utc)
    session.add(
        AnalysisSnapshot(
            company_id=company.id, ticker=ticker, as_of=now,
            financial_engine_version="v1", scoring_engine_version="bank-v1", valuation_engine_version="v1",
            prompt_version="v1", llm_model="mock", llm_is_mocked=True,
            context_json={"scores": {"overall": 60.0}, "valuation": {"pe": 5.0, "pb": pb, "ev_ebitda": None}},
            analysis_json={}, data_quality_json={}, created_at=now,
        )
    )
    await session.flush()
    return company


async def _finance_sector(session: AsyncSession) -> tuple[Industry, Industry]:
    sector = Sector(name="Finans")
    session.add(sector)
    await session.flush()
    bank = Industry(sector_id=sector.id, name="Bankacılık")
    insurance = Industry(sector_id=sector.id, name="Sigorta")
    session.add_all([bank, insurance])
    await session.flush()
    return bank, insurance


async def test_bank_never_falls_back_to_sector_peers(db_session: AsyncSession):
    bank_ind, insurance_ind = await _finance_sector(db_session)
    await _company(db_session, "BANKA", bank_ind, pb=1.0)
    await _company(db_session, "SGRTA", insurance_ind, pb=2.0)
    await db_session.commit()

    result = await compute_peer_comparison(db_session, "BANKA")
    assert result.peer_group_basis == "none"
    assert result.peer_count == 0


async def test_non_bank_financial_sector_fallback_excludes_banks(db_session: AsyncSession):
    bank_ind, insurance_ind = await _finance_sector(db_session)
    await _company(db_session, "BANKA", bank_ind, pb=1.0)
    await _company(db_session, "SGRTA", insurance_ind, pb=2.0)
    await db_session.commit()

    result = await compute_peer_comparison(db_session, "SGRTA")
    assert result.peer_count == 0
    assert all(p.ticker != "BANKA" for p in result.peers)


async def test_bank_peer_medians_use_banks_only(db_session: AsyncSession):
    bank_ind, insurance_ind = await _finance_sector(db_session)
    subject = await _company(db_session, "BANKA", bank_ind, pb=1.0)
    await _company(db_session, "BANKB", bank_ind, pb=0.8)
    await _company(db_session, "BANKC", bank_ind, pb=1.2)
    await _company(db_session, "SGRTA", insurance_ind, pb=9.0)
    await db_session.commit()

    medians = await peer_medians_for_company(db_session, subject)
    assert medians.peer_count == 2
    assert medians.median_pb == 1.0
    assert medians.pb_count == 2
