from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.providers.base import (
    CompanyDataProvider,
    DisclosureProvider,
    FinancialDataProvider,
    MacroDataProvider,
    MarketDataProvider,
)
from app.providers.company.yfinance_company_provider import YFinanceCompanyDataProvider
from app.providers.disclosure.kap_provider import KapDisclosureProvider
from app.providers.financial.yfinance_provider import YFinanceFinancialDataProvider
from app.providers.macro.macro_provider import CompositeMacroDataProvider
from app.providers.market.yfinance_provider import YFinanceMarketDataProvider


@dataclass
class ProviderBundle:
    company: CompanyDataProvider
    market: MarketDataProvider
    financial: FinancialDataProvider
    disclosure: DisclosureProvider
    macro: MacroDataProvider
    llm: LLMProvider


def build_provider_bundle(settings: Settings) -> ProviderBundle:
    llm: LLMProvider
    if settings.openai_api_key:
        llm = OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)
    else:
        llm = MockLLMProvider()

    return ProviderBundle(
        company=YFinanceCompanyDataProvider(),
        market=YFinanceMarketDataProvider(),
        financial=YFinanceFinancialDataProvider(),
        disclosure=KapDisclosureProvider(),
        macro=CompositeMacroDataProvider(evds_api_key=settings.evds_api_key),
        llm=llm,
    )


@lru_cache
def get_provider_bundle() -> ProviderBundle:
    return build_provider_bundle(get_settings())
