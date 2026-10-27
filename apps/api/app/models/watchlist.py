"""İzleme listesi (ADR-013).

Tek kullanıcılı sistem olduğu için kullanıcı kolonu yok: listedeki her satır
bir hissedir. Son toplu yenileme işinin (zamanlanmış ya da elle tetiklenmiş)
sonucu da aynı satırda tutulur — ayrı bir durum tablosu bu ölçekte gereksiz.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow

REFRESH_STATUS_SUCCESS = "SUCCESS"
REFRESH_STATUS_FAILED = "FAILED"

REFRESH_TRIGGER_SCHEDULED = "scheduled"
REFRESH_TRIGGER_MANUAL = "manual"


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("ticker", name="uq_watchlist_items_ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    added_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    # Son toplu yenileme denemesi (services/watchlist_refresh.py). Şirket
    # sayfasındaki tekil "Yenile" bunlara dokunmaz; o yenilemenin zamanı
    # zaten son AnalysisSnapshot.created_at'ten okunur.
    last_refresh_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_refresh_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_refresh_trigger: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_refresh_error: Mapped[str | None] = mapped_column(Text, nullable=True)
