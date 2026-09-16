from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import require_user
from app.schemas.peer import PeerComparisonResult
from app.services.peer_comparison import (
    CompanyNotFoundError,
    NoAnalysisSnapshotError,
    compute_peer_comparison,
)

router = APIRouter(prefix="/api/companies", tags=["peers"], dependencies=[Depends(require_user)])


@router.get("/{ticker}/analysis/peers", response_model=PeerComparisonResult)
async def get_peer_comparison(ticker: str, db: AsyncSession = Depends(get_db)):
    """Compare `ticker` against the median of already-refreshed peers in its
    industry (falling back to sector). A ticker with zero peers is still a
    valid 200 response (`insufficient_peers=True`) — not having peers yet is
    an expected state, not a failure. Only an unknown ticker, or one that has
    never itself been refreshed, is a 404."""
    try:
        return await compute_peer_comparison(db, ticker)
    except NoAnalysisSnapshotError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CompanyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
