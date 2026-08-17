from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import DisclosureCategory


class KapDisclosure(Base):
    __tablename__ = "kap_disclosures"
    __table_args__ = (
        UniqueConstraint("company_id", "kap_disclosure_index", name="uq_kap_disclosure"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    kap_disclosure_index: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[DisclosureCategory] = mapped_column(
        String(30), nullable=False, default=DisclosureCategory.OTHER
    )
    published_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_url: Mapped[str] = mapped_column(String(255), nullable=False)
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
