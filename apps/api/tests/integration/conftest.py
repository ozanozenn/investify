from __future__ import annotations

import datetime as dt

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db, get_providers
from app.core.config import Settings, get_settings
from app.llm.mock_provider import MockLLMProvider
from app.main import app
from app.models.base import Base
from app.providers.base import (
    Candle,
    CompanyDataProvider,
    DisclosureProvider,
    FinancialDataProvider,
    MacroDataProvider,
    MacroObservationDTO,
    MarketDataProvider,
    ProviderUnavailableError,
    Quote,
    RawFinancialPeriod,
)
from app.services.provider_bundle import ProviderBundle


class FakeCompanyProvider(CompanyDataProvider):
    code = "fake"

    async def get_company_profile(self, ticker: str) -> dict:
        return {
            "name": f"{ticker} Test A.Ş.",
            "sector": "Sanayi",
            "industry": "Test Industry",
            "is_financial_industry": False,
        }


class FakeMarketProvider(MarketDataProvider):
    code = "fake"
    fail = False

    async def get_quote(self, ticker: str) -> Quote:
        if self.fail:
            raise ProviderUnavailableError(self.code, "simulated failure")
        now = dt.datetime.now(dt.timezone.utc)
        return Quote(
            ticker=ticker,
            price=50.0,
            currency="TRY",
            market_cap=5000.0,
            shares_outstanding=100.0,
            fifty_two_week_high=60.0,
            fifty_two_week_low=40.0,
            as_of=now,
            source_code=self.code,
            fetched_at=now,
        )

    async def get_historical_prices(self, ticker: str, years: int = 5) -> list[Candle]:
        return [Candle(date=dt.date(2024, 12, 31), open=39, high=41, low=38, close=40, volume=1000)]


class FakeFinancialProvider(FinancialDataProvider):
    code = "fake"
    fail = False

    async def get_financial_statements(
        self, ticker: str, annual_years: int = 5, quarterly_quarters: int = 8
    ) -> list[RawFinancialPeriod]:
        if self.fail:
            raise ProviderUnavailableError(self.code, "simulated failure")
        now = dt.datetime.now(dt.timezone.utc)
        return [
            RawFinancialPeriod(
                period_type="ANNUAL",
                fiscal_year=2024,
                fiscal_quarter=None,
                period_end_date=dt.date(2024, 12, 31),
                currency="TRY",
                values={
                    "REVENUE": 1210.0,
                    "EBITDA": 250.0,
                    "NET_INCOME": 100.0,
                    "EQUITY": 620.0,
                    "TOTAL_DEBT": 330.0,
                    "CASH": 130.0,
                    "TOTAL_ASSETS": 1220.0,
                    "OPERATING_CASH_FLOW": 190.0,
                    "CAPEX": -60.0,
                },
                source_code=self.code,
                fetched_at=now,
            ),
            RawFinancialPeriod(
                period_type="ANNUAL",
                fiscal_year=2025,
                fiscal_quarter=None,
                period_end_date=dt.date(2025, 12, 31),
                currency="TRY",
                values={
                    "REVENUE": 1331.0,
                    "EBITDA": 280.0,
                    "NET_INCOME": 115.0,
                    "EQUITY": 690.0,
                    "TOTAL_DEBT": 340.0,
                    "CASH": 150.0,
                    "TOTAL_ASSETS": 1350.0,
                    "OPERATING_CASH_FLOW": 210.0,
                    "CAPEX": -65.0,
                },
                source_code=self.code,
                fetched_at=now,
            ),
        ]


class FakeDisclosureProvider(DisclosureProvider):
    code = "fake"

    async def get_disclosures(self, ticker: str, lookback_days: int = 90, limit: int = 15):
        return []


class FakeMacroProvider(MacroDataProvider):
    code = "fake"

    async def get_series(self, series_code: str, lookback_days: int = 400) -> list[MacroObservationDTO]:
        now = dt.datetime.now(dt.timezone.utc)
        return [
            MacroObservationDTO(
                series_code=series_code, observation_date=now.date(), value=42.0, is_mock=True, fetched_at=now
            )
        ]


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


@pytest.fixture
def fake_providers():
    return ProviderBundle(
        company=FakeCompanyProvider(),
        market=FakeMarketProvider(),
        financial=FakeFinancialProvider(),
        disclosure=FakeDisclosureProvider(),
        macro=FakeMacroProvider(),
        llm=MockLLMProvider(),
    )


@pytest_asyncio.fixture
async def client(db_session, fake_providers):
    async def override_get_db():
        yield db_session

    def override_get_providers():
        return fake_providers

    def override_get_settings():
        return Settings(auth_dev_bypass=True, app_env="development")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_providers] = override_get_providers
    app.dependency_overrides[get_settings] = override_get_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
