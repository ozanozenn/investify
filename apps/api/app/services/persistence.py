"""Idempotent persistence helpers (roadmap section 86: ingestion must not
duplicate rows on repeated refresh). Each function upserts by the model's
natural unique key rather than blindly inserting.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import FinancialPeriod, FinancialValue
from app.models.kap import KapDisclosure
from app.models.macro import MacroObservation, MacroSeries
from app.models.market import MarketSnapshot
from app.models.snapshots import AnalysisSnapshot, FinancialMetricSnapshot, ScoreSnapshot, ValuationSnapshot
from app.providers.base import RawDisclosure, RawFinancialPeriod
from app.providers.disclosure.kap_provider import categorize


async def upsert_financial_periods(
    session: AsyncSession, company_id: int, raw_periods: list[RawFinancialPeriod]
) -> list[FinancialPeriod]:
    saved: list[FinancialPeriod] = []
    for raw in raw_periods:
        result = await session.execute(
            select(FinancialPeriod).where(
                FinancialPeriod.company_id == company_id,
                FinancialPeriod.period_type == raw.period_type,
                FinancialPeriod.fiscal_year == raw.fiscal_year,
                FinancialPeriod.fiscal_quarter == raw.fiscal_quarter,
            )
        )
        period = result.scalar_one_or_none()
        if period is None:
            period = FinancialPeriod(
                company_id=company_id,
                period_type=raw.period_type,
                fiscal_year=raw.fiscal_year,
                fiscal_quarter=raw.fiscal_quarter,
                period_end_date=raw.period_end_date,
                currency=raw.currency,
                source_code=raw.source_code,
                fetched_at=raw.fetched_at,
            )
            session.add(period)
            await session.flush()
        else:
            period.fetched_at = raw.fetched_at

        existing_values_result = await session.execute(
            select(FinancialValue).where(FinancialValue.financial_period_id == period.id)
        )
        existing_values = {v.canonical_field: v for v in existing_values_result.scalars().all()}
        for field, value in raw.values.items():
            if field in existing_values:
                existing_values[field].value = value
                existing_values[field].fetched_at = raw.fetched_at
            else:
                session.add(
                    FinancialValue(
                        financial_period_id=period.id,
                        canonical_field=field,
                        value=value,
                        currency=raw.currency,
                        scale=1,
                        source_code=raw.source_code,
                        fetched_at=raw.fetched_at,
                    )
                )
        await session.flush()
        saved.append(period)
    return saved


async def insert_market_snapshot(session: AsyncSession, company_id: int, quote) -> MarketSnapshot:
    snapshot = MarketSnapshot(
        company_id=company_id,
        price=quote.price,
        currency=quote.currency,
        market_cap=quote.market_cap,
        shares_outstanding=quote.shares_outstanding,
        fifty_two_week_high=quote.fifty_two_week_high,
        fifty_two_week_low=quote.fifty_two_week_low,
        source_code=quote.source_code,
        as_of=quote.as_of,
        fetched_at=quote.fetched_at,
    )
    session.add(snapshot)
    await session.flush()
    return snapshot


async def upsert_kap_disclosures(
    session: AsyncSession, company_id: int, raw_disclosures: list[RawDisclosure]
) -> list[KapDisclosure]:
    saved: list[KapDisclosure] = []
    for raw in raw_disclosures:
        result = await session.execute(
            select(KapDisclosure).where(
                KapDisclosure.company_id == company_id,
                KapDisclosure.kap_disclosure_index == raw.kap_disclosure_index,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = KapDisclosure(
                company_id=company_id,
                kap_disclosure_index=raw.kap_disclosure_index,
                title=raw.title,
                subject=raw.subject,
                category=categorize(raw.subject),
                published_at=raw.published_at,
                source_url=raw.source_url,
                fetched_at=raw.fetched_at,
            )
            session.add(row)
            await session.flush()
        saved.append(row)
    return saved


async def upsert_macro_series_and_observations(
    session: AsyncSession, code: str, label: str, unit: str, source_code: str, observations
) -> MacroSeries:
    result = await session.execute(select(MacroSeries).where(MacroSeries.code == code))
    series = result.scalar_one_or_none()
    if series is None:
        series = MacroSeries(code=code, label=label, unit=unit, source_code=source_code)
        session.add(series)
        await session.flush()

    for obs in observations:
        existing = await session.execute(
            select(MacroObservation).where(
                MacroObservation.macro_series_id == series.id,
                MacroObservation.observation_date == obs.observation_date,
            )
        )
        row = existing.scalar_one_or_none()
        if row is None:
            session.add(
                MacroObservation(
                    macro_series_id=series.id,
                    observation_date=obs.observation_date,
                    value=obs.value,
                    is_mock=obs.is_mock,
                    fetched_at=obs.fetched_at,
                )
            )
        else:
            row.value = obs.value
            row.is_mock = obs.is_mock
            row.fetched_at = obs.fetched_at
    await session.flush()
    return series


async def save_metric_snapshot(
    session: AsyncSession, company_id: int, financial_period_id: int | None, engine_version: str, metrics_json: dict
) -> FinancialMetricSnapshot:
    snapshot = FinancialMetricSnapshot(
        company_id=company_id,
        financial_period_id=financial_period_id,
        engine_version=engine_version,
        metrics_json=metrics_json,
        computed_at=dt.datetime.now(dt.timezone.utc),
    )
    session.add(snapshot)
    await session.flush()
    return snapshot


async def save_valuation_snapshot(
    session: AsyncSession, company_id: int, engine_version: str, valuation_json: dict
) -> ValuationSnapshot:
    snapshot = ValuationSnapshot(
        company_id=company_id,
        engine_version=engine_version,
        valuation_json=valuation_json,
        computed_at=dt.datetime.now(dt.timezone.utc),
    )
    session.add(snapshot)
    await session.flush()
    return snapshot


async def save_score_snapshot(
    session: AsyncSession, company_id: int, engine_version: str, scores_json: dict
) -> ScoreSnapshot:
    snapshot = ScoreSnapshot(
        company_id=company_id,
        engine_version=engine_version,
        scores_json=scores_json,
        computed_at=dt.datetime.now(dt.timezone.utc),
    )
    session.add(snapshot)
    await session.flush()
    return snapshot


async def save_analysis_snapshot(
    session: AsyncSession,
    company_id: int,
    ticker: str,
    as_of: dt.datetime,
    financial_engine_version: str,
    scoring_engine_version: str,
    valuation_engine_version: str,
    prompt_version: str,
    llm_model: str,
    llm_is_mocked: bool,
    context_json: dict,
    analysis_json: dict,
    data_quality_json: dict,
) -> AnalysisSnapshot:
    snapshot = AnalysisSnapshot(
        company_id=company_id,
        ticker=ticker,
        as_of=as_of,
        financial_engine_version=financial_engine_version,
        scoring_engine_version=scoring_engine_version,
        valuation_engine_version=valuation_engine_version,
        prompt_version=prompt_version,
        llm_model=llm_model,
        llm_is_mocked=llm_is_mocked,
        context_json=context_json,
        analysis_json=analysis_json,
        data_quality_json=data_quality_json,
        created_at=dt.datetime.now(dt.timezone.utc),
    )
    session.add(snapshot)
    await session.flush()
    return snapshot
