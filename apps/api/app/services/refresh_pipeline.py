"""The refresh pipeline (roadmap section 36 / Phase 1 section 14).

ticker -> company profile -> market data -> financials -> KAP -> macro ->
normalize -> financial metrics -> valuation -> scoring -> structured
context -> LLM interpretation -> persist AnalysisSnapshot.

Every provider stage is wrapped so a single failure degrades the result
instead of crashing the whole refresh (section 37). Stage outcomes are
logged to `DataFetchLog` and returned in `RefreshResult.stage_results` so
the API/UI can show "X data unavailable" (section 3.13/23).
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_analysis_config, get_tcmb_calendar_config, get_verdict_config
from app.core.logging import get_logger
from app.financial_engine import formulas
from app.financial_engine.engine import compute_financial_metrics
from app.financial_engine.industry_strategy import UNSUPPORTED_INDUSTRY_MESSAGE, is_generic_engine_supported
from app.llm.base import LLMProviderError
from app.models.data_source import DataFetchLog
from app.models.enums import FetchStatus
from app.providers.base import Candle, ProviderUnavailableError, Quote, RawDisclosure, RawFinancialPeriod
from app.schemas.context import (
    CompanyContext,
    DisclosureContext,
    MacroSeriesPoint,
    MarketContext,
    SourceRef,
    StructuredAnalysisContext,
)
from app.schemas.financial import FinancialHistoryPoint, FinancialMetrics, PeriodData
from app.schemas.scoring import ScoreResult
from app.schemas.valuation import ValuationMetrics
from app.scoring_engine.engine import compute_score, unsupported_score_result
from app.services import persistence
from app.services.company_bootstrap import get_or_create_company
from app.services.context_builder import build_context
from app.services.data_quality import compute_data_quality
from app.services.llm_analysis import analyze_with_hallucination_retry
from app.services.peer_comparison import peer_medians_for_company
from app.services.provider_bundle import ProviderBundle
from app.services.quality_analysis import compute_quality_analysis
from app.valuation_engine.dcf import compute_dcf
from app.valuation_engine.engine import compute_valuation
from app.verdict_engine.engine import compute_verdict
from app.verdict_engine.history_labels import label_history_multiples

logger = get_logger(__name__)


def _next_rate_decision_date() -> dt.date | None:
    """Nearest upcoming TCMB PPK meeting date, if any is still known in
    `config/tcmb_calendar.yaml` — gives the LLM one concrete, real
    near-term macro date to reference instead of inventing one."""
    today = dt.date.today()
    upcoming = sorted(
        d
        for d in (dt.date.fromisoformat(m["date"]) for m in get_tcmb_calendar_config()["meetings"])
        if d >= today
    )
    return upcoming[0] if upcoming else None


@dataclass
class RefreshResult:
    context: StructuredAnalysisContext
    analysis: dict
    stage_results: dict[str, str]
    llm_is_mocked: bool
    prompt_version: str
    llm_model: str


async def _log_stage(
    session: AsyncSession,
    request_id: str,
    ticker: str,
    provider_code: str,
    operation: str,
    status: FetchStatus,
    started_at: dt.datetime,
    error: str | None = None,
) -> None:
    finished_at = dt.datetime.now(dt.timezone.utc)
    session.add(
        DataFetchLog(
            request_id=request_id,
            ticker=ticker,
            data_source_id=None,
            provider_code=provider_code,
            operation=operation,
            status=status,
            latency_ms=(finished_at - started_at).total_seconds() * 1000,
            error_message=error,
            started_at=started_at,
            finished_at=finished_at,
        )
    )
    await session.flush()


def _raw_period_to_period_data(raw: RawFinancialPeriod) -> PeriodData:
    return PeriodData(
        period_type=raw.period_type,
        fiscal_year=raw.fiscal_year,
        fiscal_quarter=raw.fiscal_quarter,
        period_end_date=raw.period_end_date,
        values=raw.values,
    )


async def run_refresh(
    session: AsyncSession,
    ticker: str,
    providers: ProviderBundle,
    settings: Settings,
    request_id: str | None = None,
) -> RefreshResult:
    request_id = request_id or str(uuid.uuid4())
    ticker = ticker.upper()
    analysis_cfg = get_analysis_config()

    company = await get_or_create_company(session, ticker, providers.company)
    await session.commit()

    stage_results: dict[str, str] = {}
    sources: list[SourceRef] = []

    # --- Market data ---
    quote: Quote | None = None
    candles: list[Candle] = []
    started = dt.datetime.now(dt.timezone.utc)
    try:
        quote = await providers.market.get_quote(ticker)
        candles = await providers.market.get_historical_prices(ticker, years=analysis_cfg["valuation"]["historical_lookback_years"])
        await persistence.insert_market_snapshot(session, company.id, quote)
        stage_results["market"] = "SUCCESS"
        sources.append(
            SourceRef(field="market", source=quote.source_code, fetched_at=quote.fetched_at)
        )
        await _log_stage(session, request_id, ticker, providers.market.code, "get_quote", FetchStatus.SUCCESS, started)
    except ProviderUnavailableError as exc:
        stage_results["market"] = "FAILED"
        await _log_stage(session, request_id, ticker, providers.market.code, "get_quote", FetchStatus.FAILED, started, str(exc))
        logger.warning("market_stage_failed", extra={"ticker": ticker, "error": str(exc)})

    # --- Financial statements ---
    raw_periods: list[RawFinancialPeriod] = []
    started = dt.datetime.now(dt.timezone.utc)
    try:
        raw_periods = await providers.financial.get_financial_statements(
            ticker,
            annual_years=analysis_cfg["history"]["annual_years"],
            quarterly_quarters=analysis_cfg["history"]["quarterly_quarters"],
        )
        await persistence.upsert_financial_periods(session, company.id, raw_periods)
        stage_results["financials"] = "SUCCESS"
        if raw_periods:
            sources.append(
                SourceRef(field="financials", source=raw_periods[0].source_code, fetched_at=raw_periods[0].fetched_at)
            )
        await _log_stage(session, request_id, ticker, providers.financial.code, "get_financial_statements", FetchStatus.SUCCESS, started)
    except ProviderUnavailableError as exc:
        stage_results["financials"] = "FAILED"
        await _log_stage(session, request_id, ticker, providers.financial.code, "get_financial_statements", FetchStatus.FAILED, started, str(exc))
        logger.warning("financials_stage_failed", extra={"ticker": ticker, "error": str(exc)})

    # --- KAP disclosures ---
    disclosure_contexts: list[DisclosureContext] = []
    started = dt.datetime.now(dt.timezone.utc)
    try:
        raw_disclosures: list[RawDisclosure] = await providers.disclosure.get_disclosures(
            ticker,
            lookback_days=analysis_cfg["kap"]["lookback_days"],
            limit=analysis_cfg["kap"]["max_disclosures_returned"],
        )
        saved = await persistence.upsert_kap_disclosures(session, company.id, raw_disclosures)
        stage_results["kap"] = "SUCCESS"
        for row in saved:
            disclosure_contexts.append(
                DisclosureContext(
                    title=row.title, category=row.category, published_at=row.published_at, source_url=row.source_url
                )
            )
            sources.append(SourceRef(field="kap_disclosure", source="kap", source_url=row.source_url, fetched_at=row.fetched_at, published_at=row.published_at))
        await _log_stage(session, request_id, ticker, providers.disclosure.code, "get_disclosures", FetchStatus.SUCCESS, started)
    except ProviderUnavailableError as exc:
        stage_results["kap"] = "FAILED"
        await _log_stage(session, request_id, ticker, providers.disclosure.code, "get_disclosures", FetchStatus.FAILED, started, str(exc))
        logger.warning("kap_stage_failed", extra={"ticker": ticker, "error": str(exc)})

    # --- Macro context ---
    macro_points: list[MacroSeriesPoint] = []
    for series_cfg in analysis_cfg["macro"]["series"]:
        code, label = series_cfg["code"], series_cfg["label"]
        started = dt.datetime.now(dt.timezone.utc)
        try:
            obs = await providers.macro.get_series(code)
            await persistence.upsert_macro_series_and_observations(
                session, code, label, unit=None, source_code=providers.macro.code, observations=obs
            )
            if obs:
                latest = obs[-1]
                macro_points.append(
                    MacroSeriesPoint(
                        code=code, label=label, value=latest.value, observation_date=latest.observation_date, is_mock=latest.is_mock
                    )
                )
                sources.append(
                    SourceRef(field=f"macro:{code}", source=providers.macro.code, fetched_at=latest.fetched_at, is_mock=latest.is_mock)
                )
            stage_results[f"macro:{code}"] = "SUCCESS"
            await _log_stage(session, request_id, ticker, providers.macro.code, f"get_series:{code}", FetchStatus.SUCCESS, started)
        except ProviderUnavailableError as exc:
            stage_results[f"macro:{code}"] = "FAILED"
            await _log_stage(session, request_id, ticker, providers.macro.code, f"get_series:{code}", FetchStatus.FAILED, started, str(exc))
            logger.warning("macro_stage_failed", extra={"ticker": ticker, "series": code, "error": str(exc)})

    await session.commit()

    # --- Deterministic engines ---
    annual_period_data = [_raw_period_to_period_data(p) for p in raw_periods if p.period_type == "ANNUAL"]
    annual_period_data.sort(key=lambda p: p.fiscal_year)
    financial_history = [
        FinancialHistoryPoint(
            fiscal_year=p.fiscal_year,
            revenue=p.values.get("REVENUE"),
            ebitda=p.values.get("EBITDA"),
            net_income=p.values.get("NET_INCOME"),
            free_cash_flow=p.values.get("FREE_CASH_FLOW")
            or formulas.free_cash_flow(p.values.get("OPERATING_CASH_FLOW"), p.values.get("CAPEX")),
        )
        for p in annual_period_data
    ]
    unsupported_reason = None if is_generic_engine_supported(company.is_financial_industry) else UNSUPPORTED_INDUSTRY_MESSAGE

    if unsupported_reason:
        metrics = FinancialMetrics(as_of_period="N/A", missing_fields=["unsupported_industry"])
        valuation = ValuationMetrics(missing_fields=["unsupported_industry"])
        scores: ScoreResult = unsupported_score_result(settings.scoring_engine_version, unsupported_reason)
    else:
        metrics = compute_financial_metrics(annual_period_data)
        valuation = compute_valuation(
            current_price=quote.price if quote else None,
            market_cap=quote.market_cap if quote else None,
            shares_outstanding=quote.shares_outstanding if quote else None,
            latest_period=annual_period_data[-1] if annual_period_data else None,
            historical_periods=annual_period_data,
            historical_candles=candles,
            lookback_years=analysis_cfg["valuation"]["historical_lookback_years"],
        )
        # Değerleme kutucuklarının etiketleri hüküm kartıyla aynı eşiklerden.
        history_cfg = get_verdict_config()["lenses"]["history"]
        valuation = label_history_multiples(
            valuation, cheap_below=history_cfg["cheap_below"], expensive_above=history_cfg["expensive_above"]
        )
        score_inputs = {
            **metrics.model_dump(),
            "pe_vs_history_ratio": valuation.pe_vs_history_ratio,
            "ev_ebitda_vs_history_ratio": valuation.ev_ebitda_vs_history_ratio,
            "pb_vs_history_ratio": valuation.pb_vs_history_ratio,
        }
        scores = compute_score(score_inputs, settings.scoring_engine_version)

        # Base-case DCF ships with every refresh (roadmap section 13); the
        # dedicated /analysis/dcf endpoint additionally supports on-demand
        # recompute with user-overridden assumptions without a full refresh.
        valuation.dcf = compute_dcf(
            latest_period=annual_period_data[-1] if annual_period_data else None,
            historical_periods=annual_period_data,
            current_price=quote.price if quote else None,
            market_cap=quote.market_cap if quote else None,
            net_debt=metrics.net_debt,
            shares_outstanding=quote.shares_outstanding if quote else None,
        )

    await persistence.save_metric_snapshot(session, company.id, None, settings.financial_engine_version, metrics.model_dump(mode="json"))
    await persistence.save_valuation_snapshot(session, company.id, settings.valuation_engine_version, valuation.model_dump(mode="json"))
    await persistence.save_score_snapshot(session, company.id, settings.scoring_engine_version, scores.model_dump(mode="json"))
    await session.commit()

    data_quality = compute_data_quality(metrics, stage_results, market_available=quote is not None)

    peer_medians = None
    if not unsupported_reason:
        try:
            peer_medians = await peer_medians_for_company(session, company)
        except Exception as exc:  # hüküm sektör yöntemi olmadan devam eder
            logger.warning("peer_medians_failed", extra={"ticker": ticker, "error": str(exc)})
    verdict = compute_verdict(
        valuation=valuation,
        scores=scores,
        data_quality_overall=data_quality.overall,
        peers=peer_medians,
        config=get_verdict_config(),
        unsupported_reason=unsupported_reason,
    )

    company_context = CompanyContext(
        ticker=ticker,
        name=company.name,
        sector=company.industry.sector.name if company.industry else None,
        industry=company.industry.name if company.industry else None,
        description=company.description,
        is_financial_industry=company.is_financial_industry,
    )
    market_context = MarketContext(
        price=quote.price if quote else None,
        currency=quote.currency if quote else "TRY",
        market_cap=quote.market_cap if quote else None,
        fifty_two_week_high=quote.fifty_two_week_high if quote else None,
        fifty_two_week_low=quote.fifty_two_week_low if quote else None,
        as_of=quote.as_of if quote else None,
    )

    context = build_context(
        ticker=ticker,
        company=company_context,
        market=market_context,
        metrics=metrics,
        financial_history=financial_history,
        valuation=valuation,
        scores=scores,
        macro=macro_points,
        disclosures=disclosure_contexts,
        data_quality=data_quality,
        sources=sources,
        unsupported_reason=unsupported_reason,
        next_rate_decision_date=_next_rate_decision_date(),
        verdict=verdict,
    )
    # Kalite bayrakları + reel büyüme (ADR-016) — LLM'den önce context'e girer.
    context.quality_flags, context.real_growth = compute_quality_analysis(
        annual_period_data, macro_points, unsupported_reason
    )

    try:
        # Bayraklı sayı varsa bir kez düzeltme denemesi yapar (ADR-003).
        guarded = await analyze_with_hallucination_retry(providers.llm, context, settings.llm_prompt_version)
    except LLMProviderError as exc:
        logger.error("llm_stage_failed", extra={"ticker": ticker, "error": str(exc)})
        raise

    analysis_dict = guarded.result.model_dump(mode="json")
    analysis_dict["_meta"] = {
        "llm_model": providers.llm.model,
        "llm_is_mocked": providers.llm.is_mock,
        "prompt_version": settings.llm_prompt_version,
        **guarded.meta(),
    }

    await persistence.save_analysis_snapshot(
        session,
        company_id=company.id,
        ticker=ticker,
        as_of=context.as_of,
        financial_engine_version=settings.financial_engine_version,
        scoring_engine_version=settings.scoring_engine_version,
        valuation_engine_version=settings.valuation_engine_version,
        prompt_version=settings.llm_prompt_version,
        llm_model=providers.llm.model,
        llm_is_mocked=providers.llm.is_mock,
        context_json=context.model_dump(mode="json"),
        analysis_json=analysis_dict,
        data_quality_json=data_quality.model_dump(mode="json"),
    )
    await session.commit()

    return RefreshResult(
        context=context,
        analysis=analysis_dict,
        stage_results=stage_results,
        llm_is_mocked=providers.llm.is_mock,
        prompt_version=settings.llm_prompt_version,
        llm_model=providers.llm.model,
    )
