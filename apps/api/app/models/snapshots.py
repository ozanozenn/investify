from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# JSONB on Postgres, plain JSON elsewhere (e.g. SQLite in unit tests).
JSONType = JSONB().with_variant(JSON(), "sqlite")


class FinancialMetricSnapshot(Base):
    __tablename__ = "financial_metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    financial_period_id: Mapped[int | None] = mapped_column(
        ForeignKey("financial_periods.id"), nullable=True
    )
    engine_version: Mapped[str] = mapped_column(String(10), nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSONType, nullable=False)
    computed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ValuationSnapshot(Base):
    __tablename__ = "valuation_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    engine_version: Mapped[str] = mapped_column(String(10), nullable=False)
    valuation_json: Mapped[dict] = mapped_column(JSONType, nullable=False)
    computed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScoreSnapshot(Base):
    __tablename__ = "score_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    engine_version: Mapped[str] = mapped_column(String(10), nullable=False)
    scores_json: Mapped[dict] = mapped_column(JSONType, nullable=False)
    computed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AnalysisSnapshot(Base):
    """Immutable record of one refresh run — the reproducibility backbone (ADR-005)."""

    __tablename__ = "analysis_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    as_of: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    financial_engine_version: Mapped[str] = mapped_column(String(10), nullable=False)
    scoring_engine_version: Mapped[str] = mapped_column(String(10), nullable=False)
    valuation_engine_version: Mapped[str] = mapped_column(String(10), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_is_mocked: Mapped[bool] = mapped_column(nullable=False, default=False)
    context_json: Mapped[dict] = mapped_column(JSONType, nullable=False)
    analysis_json: Mapped[dict] = mapped_column(JSONType, nullable=False)
    data_quality_json: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
