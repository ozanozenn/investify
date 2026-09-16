from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel


class PeerCompanyMetric(BaseModel):
    """One company's latest scored/valued snapshot, as used in a peer comparison."""

    ticker: str
    name: str
    overall_score: float | None
    pe: float | None
    pb: float | None
    ev_ebitda: float | None
    as_of: dt.datetime


class PeerComparisonResult(BaseModel):
    """Result of comparing one company against the median of its already-refreshed
    industry (falling back to sector) peers. Deliberately honest when there is no
    peer data yet — see `insufficient_peers` / `insufficient_peers_reason` rather
    than fabricating a median from too few data points."""

    ticker: str
    sector: str | None
    industry: str | None
    peer_group_basis: Literal["industry", "sector", "none"]
    peer_count: int
    peers: list[PeerCompanyMetric]
    this_company: PeerCompanyMetric
    median_overall_score: float | None
    median_pe: float | None
    median_pb: float | None
    median_ev_ebitda: float | None
    overall_score_vs_median: float | None
    insufficient_peers: bool
    insufficient_peers_reason: str | None = None
