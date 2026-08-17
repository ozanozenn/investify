from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MacroSeries(Base, TimestampMixin):
    __tablename__ = "macro_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_code: Mapped[str] = mapped_column(String(50), nullable=False)

    observations: Mapped[list["MacroObservation"]] = relationship(back_populates="series")


class MacroObservation(Base):
    __tablename__ = "macro_observations"
    __table_args__ = (
        UniqueConstraint("macro_series_id", "observation_date", name="uq_macro_observation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    macro_series_id: Mapped[int] = mapped_column(ForeignKey("macro_series.id"), nullable=False)
    observation_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    series: Mapped[MacroSeries] = relationship(back_populates="observations")
