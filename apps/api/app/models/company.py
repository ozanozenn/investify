from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Sector(Base, TimestampMixin):
    __tablename__ = "sectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    industries: Mapped[list["Industry"]] = relationship(back_populates="sector")


class Industry(Base, TimestampMixin):
    __tablename__ = "industries"
    __table_args__ = (UniqueConstraint("sector_id", "name", name="uq_industry_sector_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sector_id: Mapped[int] = mapped_column(ForeignKey("sectors.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    sector: Mapped[Sector] = relationship(back_populates="industries")
    companies: Mapped[list["Company"]] = relationship(back_populates="industry")


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry_id: Mapped[int | None] = mapped_column(ForeignKey("industries.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    investor_relations_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kap_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kap_member_oid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    founded_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    is_financial_industry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    industry: Mapped[Industry | None] = relationship(back_populates="companies")
    tickers: Mapped[list["Ticker"]] = relationship(back_populates="company")


class Ticker(Base, TimestampMixin):
    __tablename__ = "tickers"
    __table_args__ = (UniqueConstraint("symbol", "exchange", name="uq_ticker_symbol_exchange"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False, default="BIST")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    company: Mapped[Company] = relationship(back_populates="tickers")
