"""Snapshot diff / thesis tracking endpoint (roadmap sections 25/26).

Self-contained router — not yet wired into `app/main.py`; that is done by
the Phase 2 integration pass (see `docs/PHASE_2_PLAN.md`), so this file
does not touch any existing tracked file.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import require_user
from app.models.snapshots import AnalysisSnapshot
from app.schemas.diff import SnapshotDiffResult
from app.services.snapshot_diff import compute_snapshot_diff

router = APIRouter(prefix="/api/companies", tags=["comparisons"], dependencies=[Depends(require_user)])


@router.get("/{ticker}/analysis/compare", response_model=SnapshotDiffResult)
async def compare_snapshots(
    ticker: str,
    from_id: int | None = Query(default=None, description="Older snapshot id. Defaults to the second-latest."),
    to_id: int | None = Query(default=None, description="Newer snapshot id. Defaults to the latest."),
    db: AsyncSession = Depends(get_db),
):
    """Diff ("Since previous analysis") between two snapshots of `ticker`.

    Error handling (an explicit, honest state per the codebase's
    `missing_fields`/`unsupported_reason` convention, not a bug):
    - 404 when the ticker has no analysis snapshots at all (nothing to
      compare against — same "not found" semantics as a missing resource).
    - 409 when the ticker has fewer than 2 snapshots yet — the resource
      (the ticker's analysis history) exists but is not yet in a state
      that supports a comparison; the client should retry after another
      `/refresh`. 409 Conflict was chosen over 422 because the request
      itself is perfectly well-formed, it is the *current server state*
      that cannot satisfy it yet.
    - 404 when an explicit `from_id`/`to_id` does not belong to `ticker`
      (never let one ticker's ids leak another ticker's snapshot row).
    """
    ticker = ticker.upper()

    result = await db.execute(
        select(AnalysisSnapshot)
        .where(AnalysisSnapshot.ticker == ticker)
        .order_by(AnalysisSnapshot.created_at.desc())
    )
    snapshots = result.scalars().all()

    if not snapshots:
        raise HTTPException(status_code=404, detail=f"No analysis snapshots found for {ticker}.")

    if len(snapshots) < 2:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{ticker} has only {len(snapshots)} analysis snapshot(s); "
                "run at least two refreshes to compare."
            ),
        )

    by_id = {s.id: s for s in snapshots}  # snapshots already scoped to `ticker` above

    if to_id is None:
        to_snapshot = snapshots[0]  # newest-first ordering
    else:
        to_snapshot = by_id.get(to_id)
        if to_snapshot is None:
            raise HTTPException(status_code=404, detail=f"Snapshot {to_id} not found for {ticker}.")

    if from_id is None:
        # The snapshot immediately preceding `to_snapshot` in this ticker's
        # own history (list is newest-first, so the next one after removing
        # `to_snapshot` is the second-latest relative to it).
        older = [s for s in snapshots if s.id != to_snapshot.id]
        from_snapshot = older[0]
    else:
        from_snapshot = by_id.get(from_id)
        if from_snapshot is None:
            raise HTTPException(status_code=404, detail=f"Snapshot {from_id} not found for {ticker}.")

    return compute_snapshot_diff(previous=from_snapshot, current=to_snapshot)
