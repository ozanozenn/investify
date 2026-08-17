from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import CanonicalField, PeriodType


class FinancialPeriod(Base, TimestampMixin):
    __tablename__ = "financial_periods"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "period_type",
            "fiscal_year",
            "fiscal_quarter",
            name="uq_financial_period",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    period_type: Mapped[PeriodType] = mapped_column(String(20), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period_end_date: Mapped[dt.date] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="TRY")
    source_code: Mapped[str] = mapped_column(String(50), nullable=False)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    values: Mapped[list["FinancialValue"]] = relationship(
        back_populates="period", cascade="all, delete-orphan"
    )


class FinancialValue(Base):
    __tablename__ = "financial_values"
    __table_args__ = (
        UniqueConstraint("financial_period_id", "canonical_field", name="uq_financial_value"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    financial_period_id: Mapped[int] = mapped_column(
        ForeignKey("financial_periods.id"), nullable=False, index=True
    )
    canonical_field: Mapped[CanonicalField] = mapped_column(String(30), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(24, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="TRY")
    scale: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_code: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    period: Mapped[FinancialPeriod] = relationship(back_populates="values")

    @property
    def base_value(self) -> float:
        """Value converted to base currency units (never mix scales — ADR-004)."""
        return float(self.value) * self.scale
