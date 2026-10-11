from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_providers
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.core.security import require_user
from app.llm.base import LLMProviderError
from app.models.company import Company, Ticker
from app.models.snapshots import AnalysisSnapshot
from app.providers.company.ticker_index import search_tickers
from app.schemas.api import CompanyAnalysisResponse, CompanySearchResult
from app.services.provider_bundle import ProviderBundle
from app.services.refresh_pipeline import run_refresh

router = APIRouter(prefix="/api/companies", tags=["companies"], dependencies=[Depends(require_user)])
logger = get_logger(__name__)

_SEARCH_LIMIT = 10


@router.get("/search", response_model=list[CompanySearchResult])
async def search_companies(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    results = search_tickers(q, limit=_SEARCH_LIMIT)
    out = [CompanySearchResult(ticker=r["ticker"], name=r["name"]) for r in results]
    seen = {r.ticker for r in out}

    # Always merge in already-bootstrapped companies from the DB (covers
    # tickers resolved live via yfinance that aren't in the static index).
    # This used to run only when the static index had zero matches, which
    # hid previously-opened companies whenever any static ticker matched.
    term = q.strip()
    rows = await db.execute(
        select(Ticker, Company)
        .join(Company, Ticker.company_id == Company.id)
        .where(Ticker.symbol.like(f"%{term.upper()}%") | Company.name.ilike(f"%{term}%"))
        .order_by(Ticker.symbol)
        .limit(_SEARCH_LIMIT)
    )
    for ticker_row, company in rows.all():
        if ticker_row.symbol not in seen:
            seen.add(ticker_row.symbol)
            out.append(CompanySearchResult(ticker=ticker_row.symbol, name=company.name))
    return out[:_SEARCH_LIMIT]


def _snapshot_to_response(snapshot: AnalysisSnapshot, stage_results: dict[str, str] | None = None) -> CompanyAnalysisResponse:
    ctx = snapshot.context_json
    return CompanyAnalysisResponse(
        ticker=snapshot.ticker,
        as_of=snapshot.as_of,
        company=ctx["company"],
        market=ctx["market"],
        metrics=ctx["metrics"],
        financial_history=ctx["financial_history"],
        valuation=ctx["valuation"],
        scores=ctx["scores"],
        macro=ctx["macro"],
        disclosures=ctx["disclosures"],
        data_quality=ctx["data_quality"],
        sources=ctx["sources"],
        analysis=snapshot.analysis_json,
        unsupported_reason=ctx.get("unsupported_reason"),
        versions={
            "financial_engine": snapshot.financial_engine_version,
            "scoring_engine": snapshot.scoring_engine_version,
            "valuation_engine": snapshot.valuation_engine_version,
            "prompt": snapshot.prompt_version,
            "llm_model": snapshot.llm_model,
        },
        stage_results=stage_results,
    )


@router.get("/{ticker}/analysis", response_model=CompanyAnalysisResponse)
async def get_company_analysis(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    providers: ProviderBundle = Depends(get_providers),
    settings: Settings = Depends(get_settings),
):
    ticker = ticker.upper()
    result = await db.execute(
        select(AnalysisSnapshot).where(AnalysisSnapshot.ticker == ticker).order_by(AnalysisSnapshot.created_at.desc()).limit(1)
    )
    snapshot = result.scalar_one_or_none()
    if snapshot is not None:
        return _snapshot_to_response(snapshot)

    # No analysis yet for this ticker — first-time lookup triggers one
    # implicit refresh (docs/ARCHITECTURE.md "Request-time vs refresh-time").
    try:
        refresh_result = await run_refresh(db, ticker, providers, settings)
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=f"Yapay zekâ analizi şu anda kullanılamıyor: {exc}") from exc

    result = await db.execute(
        select(AnalysisSnapshot).where(AnalysisSnapshot.ticker == ticker).order_by(AnalysisSnapshot.created_at.desc()).limit(1)
    )
    snapshot = result.scalar_one()
    return _snapshot_to_response(snapshot, stage_results=refresh_result.stage_results)


@router.get("/{ticker}/analysis/history")
async def get_company_analysis_history(ticker: str, db: AsyncSession = Depends(get_db)):
    """Phase 2 comparison UI will consume this; Phase 1 only needs the
    endpoint + persisted rows to exist (ADR-005)."""
    ticker = ticker.upper()
    result = await db.execute(
        select(AnalysisSnapshot).where(AnalysisSnapshot.ticker == ticker).order_by(AnalysisSnapshot.created_at.desc())
    )
    snapshots = result.scalars().all()
    return [
        {
            "id": s.id,
            "created_at": s.created_at,
            "as_of": s.as_of,
            "overall_score": s.context_json.get("scores", {}).get("overall"),
        }
        for s in snapshots
    ]


@router.post("/{ticker}/refresh", response_model=CompanyAnalysisResponse)
async def refresh_company(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    providers: ProviderBundle = Depends(get_providers),
    settings: Settings = Depends(get_settings),
):
    ticker = ticker.upper()
    try:
        refresh_result = await run_refresh(db, ticker, providers, settings)
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=f"Yapay zekâ analizi şu anda kullanılamıyor: {exc}") from exc

    result = await db.execute(
        select(AnalysisSnapshot).where(AnalysisSnapshot.ticker == ticker).order_by(AnalysisSnapshot.created_at.desc()).limit(1)
    )
    snapshot = result.scalar_one()
    return _snapshot_to_response(snapshot, stage_results=refresh_result.stage_results)
