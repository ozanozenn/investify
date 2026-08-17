"""Company bootstrap / ticker resolution (roadmap section 3.2).

Does not hardcode all BIST companies — resolves on demand via
`CompanyDataProvider` (curated seed for the Phase 1 validation set, live
yfinance profile otherwise) the first time a ticker is searched/refreshed,
then persists it so subsequent lookups are DB-only (section 85).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import Company, Industry, Sector, Ticker
from app.providers.base import CompanyDataProvider

_COMPANY_WITH_INDUSTRY = selectinload(Company.industry).selectinload(Industry.sector)


async def _get_or_create_sector(session: AsyncSession, name: str) -> Sector:
    result = await session.execute(select(Sector).where(Sector.name == name))
    sector = result.scalar_one_or_none()
    if sector is None:
        sector = Sector(name=name)
        session.add(sector)
        await session.flush()
    return sector


async def _get_or_create_industry(session: AsyncSession, sector: Sector, name: str) -> Industry:
    result = await session.execute(
        select(Industry).where(Industry.sector_id == sector.id, Industry.name == name)
    )
    industry = result.scalar_one_or_none()
    if industry is None:
        industry = Industry(sector_id=sector.id, name=name)
        session.add(industry)
        await session.flush()
    industry.sector = sector  # keep in-memory graph connected, avoid a later lazy-load
    return industry


async def get_or_create_company(
    session: AsyncSession, ticker: str, provider: CompanyDataProvider
) -> Company:
    symbol = ticker.upper()
    result = await session.execute(select(Ticker).where(Ticker.symbol == symbol))
    existing = result.scalar_one_or_none()
    if existing is not None:
        company_result = await session.execute(
            select(Company).where(Company.id == existing.company_id).options(_COMPANY_WITH_INDUSTRY)
        )
        return company_result.scalar_one()

    profile = await provider.get_company_profile(symbol)
    sector = await _get_or_create_sector(session, profile.get("sector") or "Diğer")
    industry = await _get_or_create_industry(session, sector, profile.get("industry") or "Diğer")

    company = Company(
        name=profile["name"],
        industry_id=industry.id,
        description=profile.get("description"),
        website=profile.get("website"),
        investor_relations_url=profile.get("investor_relations_url"),
        kap_url=profile.get("kap_url"),
        employee_count=profile.get("employee_count"),
        is_financial_industry=bool(profile.get("is_financial_industry", False)),
    )
    session.add(company)
    await session.flush()
    company.industry = industry  # keep in-memory graph connected, avoid a later lazy-load

    ticker_row = Ticker(company_id=company.id, symbol=symbol, exchange="BIST", is_primary=True)
    session.add(ticker_row)
    await session.flush()
    return company
