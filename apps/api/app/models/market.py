from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="TRY")
    market_cap: Mapped[float | None] = mapped_column(Numeric(24, 2), nullable=True)
    shares_outstanding: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fifty_two_week_high: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    fifty_two_week_low: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    source_code: Mapped[str] = mapped_column(String(50), nullable=False)
    as_of: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
