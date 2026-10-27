from __future__ import annotations

import statistics

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, Industry, Sector, Ticker
from app.models.snapshots import AnalysisSnapshot
from app.schemas.peer import PeerCompanyMetric, PeerComparisonResult
from app.verdict_engine.engine import PeerMedians


class CompanyNotFoundError(ValueError):
    """No `Company`/`Ticker` row exists for the requested ticker."""


class NoAnalysisSnapshotError(ValueError):
    """The subject company exists but has never been refreshed (no
    `AnalysisSnapshot` row yet). The router turns this into a 404 asking the
    caller to run a refresh first."""


def _metric_from_snapshot(ticker: str, name: str, snapshot: AnalysisSnapshot) -> PeerCompanyMetric:
    ctx = snapshot.context_json
    scores = ctx.get("scores") or {}
    valuation = ctx.get("valuation") or {}
    return PeerCompanyMetric(
        ticker=ticker,
        name=name,
        overall_score=scores.get("overall"),
        pe=valuation.get("pe"),
        pb=valuation.get("pb"),
        ev_ebitda=valuation.get("ev_ebitda"),
        as_of=snapshot.as_of,
    )


async def _latest_snapshots_by_company(
    session: AsyncSession, company_ids: list[int]
) -> dict[int, AnalysisSnapshot]:
    """Latest `AnalysisSnapshot` per company_id, for the given companies.

    Implementation note: rather than a SQL window function (whose syntax
    behaves slightly differently across SQLite and Postgres), we fetch every
    snapshot row for these companies ordered by `created_at` descending and
    keep the first one seen per `company_id` in Python. Correct on both
    backends; fine at this data scale (one snapshot row per refresh run).
    """
    if not company_ids:
        return {}
    result = await session.execute(
        select(AnalysisSnapshot)
        .where(AnalysisSnapshot.company_id.in_(company_ids))
        .order_by(AnalysisSnapshot.created_at.desc())
    )
    latest: dict[int, AnalysisSnapshot] = {}
    for snapshot in result.scalars().all():
        latest.setdefault(snapshot.company_id, snapshot)
    return latest


async def _primary_ticker_symbol(session: AsyncSession, company: Company) -> str:
    result = await session.execute(
        select(Ticker)
        .where(Ticker.company_id == company.id)
        .order_by(Ticker.is_primary.desc(), Ticker.id.asc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row.symbol if row is not None else company.name


async def _find_peer_candidates(
    session: AsyncSession, subject: Company
) -> tuple[str, str | None, str | None, list[Company]]:
    """(peer_group_basis, sector_name, industry_name, candidates): önce aynı
    endüstri, yoksa aynı sektör; yalnızca en az bir snapshot'ı olan şirketler."""
    subject_industry: Industry | None = None
    if subject.industry_id is not None:
        subject_industry = await session.get(Industry, subject.industry_id)

    sector_name: str | None = None
    industry_name: str | None = None
    if subject_industry is not None:
        industry_name = subject_industry.name
        subject_sector = await session.get(Sector, subject_industry.sector_id)
        sector_name = subject_sector.name if subject_sector is not None else None

    peer_group_basis: str = "none"
    candidate_companies: list[Company] = []

    if subject_industry is not None:
        # Step 1: same industry, excluding the subject itself and any
        # financial/non-financial mismatch (banks are never comparable to
        # industrials even when a taxonomy nests them under one sector —
        # same discipline as financial_engine/industry_strategy.py).
        result = await session.execute(
            select(Company).where(
                Company.industry_id == subject_industry.id,
                Company.id != subject.id,
                Company.is_financial_industry == subject.is_financial_industry,
            )
        )
        industry_candidates = result.scalars().all()
        if industry_candidates:
            latest = await _latest_snapshots_by_company(session, [c.id for c in industry_candidates])
            with_data = [c for c in industry_candidates if c.id in latest]
            if with_data:
                candidate_companies = with_data
                peer_group_basis = "industry"

        # Step 2: fall back to the whole sector (any industry under it,
        # excluding the subject's own company) if industry yielded nothing.
        if not candidate_companies:
            result = await session.execute(
                select(Company)
                .join(Industry, Company.industry_id == Industry.id)
                .where(
                    Industry.sector_id == subject_industry.sector_id,
                    Company.id != subject.id,
                    Company.is_financial_industry == subject.is_financial_industry,
                )
            )
            sector_candidates = result.scalars().all()
            if sector_candidates:
                latest = await _latest_snapshots_by_company(session, [c.id for c in sector_candidates])
                with_data = [c for c in sector_candidates if c.id in latest]
                if with_data:
                    candidate_companies = with_data
                    peer_group_basis = "sector"

    return peer_group_basis, sector_name, industry_name, candidate_companies


def _median(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return statistics.median(present)


async def peer_medians_for_company(session: AsyncSession, subject: Company) -> PeerMedians:
    """Hüküm motoru için sektör medyanları (ADR-011). Konunun kendi snapshot'ı
    gerekmez — refresh sırasında, snapshot yazılmadan önce çağrılır."""
    _, _, _, candidates = await _find_peer_candidates(session, subject)
    latest = await _latest_snapshots_by_company(session, [c.id for c in candidates])
    metrics = [_metric_from_snapshot("", c.name, latest[c.id]) for c in candidates if c.id in latest]
    def positive(values: list[float | None]) -> list[float]:
        return [v for v in values if v is not None and v > 0]

    pe = positive([m.pe for m in metrics])
    ev_ebitda = positive([m.ev_ebitda for m in metrics])
    pb = positive([m.pb for m in metrics])
    return PeerMedians(
        peer_count=len(metrics),
        median_pe=_median(pe),
        median_ev_ebitda=_median(ev_ebitda),
        median_pb=_median(pb),
        pe_count=len(pe),
        ev_ebitda_count=len(ev_ebitda),
        pb_count=len(pb),
    )


async def compute_peer_comparison(session: AsyncSession, ticker: str) -> PeerComparisonResult:
    """Compare `ticker`'s latest analysis against the median of OTHER
    already-refreshed companies in the same industry, falling back to the
    same sector if the industry has no other refreshed peers.

    Raises `CompanyNotFoundError` if the ticker doesn't resolve to a company,
    and `NoAnalysisSnapshotError` if the subject company has never been
    refreshed. Both are plain `ValueError` subclasses; the router maps them
    to 404s. A subject with zero peers is NOT an error — it's returned as a
    normal 200 with `insufficient_peers=True`, mirroring the engines'
    "unsupported" pattern (`scoring_engine/engine.py:unsupported_score_result`,
    `financial_engine/industry_strategy.py`) rather than fabricating a median.
    """
    symbol = ticker.upper()

    result = await session.execute(select(Ticker).where(Ticker.symbol == symbol))
    ticker_row = result.scalars().first()
    if ticker_row is None:
        raise CompanyNotFoundError(f"'{symbol}' koduna karşılık gelen bir şirket bulunamadı")

    subject = await session.get(Company, ticker_row.company_id)
    if subject is None:
        raise CompanyNotFoundError(f"'{symbol}' koduna karşılık gelen bir şirket bulunamadı")

    subject_snapshot_result = await session.execute(
        select(AnalysisSnapshot)
        .where(AnalysisSnapshot.company_id == subject.id)
        .order_by(AnalysisSnapshot.created_at.desc())
        .limit(1)
    )
    subject_snapshot = subject_snapshot_result.scalar_one_or_none()
    if subject_snapshot is None:
        raise NoAnalysisSnapshotError(f"'{symbol}' için henüz bir analiz yok; önce bir refresh çalıştırın")

    this_company = _metric_from_snapshot(symbol, subject.name, subject_snapshot)

    peer_group_basis, sector_name, industry_name, candidate_companies = await _find_peer_candidates(
        session, subject
    )

    if not candidate_companies:
        return PeerComparisonResult(
            ticker=symbol,
            sector=sector_name,
            industry=industry_name,
            peer_group_basis="none",
            peer_count=0,
            peers=[],
            this_company=this_company,
            median_overall_score=None,
            median_pe=None,
            median_pb=None,
            median_ev_ebitda=None,
            overall_score_vs_median=None,
            insufficient_peers=True,
            insufficient_peers_reason="no_other_companies_refreshed_in_industry_or_sector",
        )

    latest_by_company = await _latest_snapshots_by_company(session, [c.id for c in candidate_companies])

    peers: list[PeerCompanyMetric] = []
    for company in candidate_companies:
        snapshot = latest_by_company.get(company.id)
        if snapshot is None:
            continue
        symbol_for_peer = await _primary_ticker_symbol(session, company)
        peers.append(_metric_from_snapshot(symbol_for_peer, company.name, snapshot))

    median_overall_score = _median([p.overall_score for p in peers])
    median_pe = _median([p.pe for p in peers])
    median_pb = _median([p.pb for p in peers])
    median_ev_ebitda = _median([p.ev_ebitda for p in peers])

    overall_score_vs_median = (
        this_company.overall_score - median_overall_score
        if this_company.overall_score is not None and median_overall_score is not None
        else None
    )

    return PeerComparisonResult(
        ticker=symbol,
        sector=sector_name,
        industry=industry_name,
        peer_group_basis=peer_group_basis,
        peer_count=len(peers),
        peers=peers,
        this_company=this_company,
        median_overall_score=median_overall_score,
        median_pe=median_pe,
        median_pb=median_pb,
        median_ev_ebitda=median_ev_ebitda,
        overall_score_vs_median=overall_score_vs_median,
        insufficient_peers=len(peers) == 0,
        insufficient_peers_reason=(
            "no_other_companies_refreshed_in_industry_or_sector" if len(peers) == 0 else None
        ),
    )
