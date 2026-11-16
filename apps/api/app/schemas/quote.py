"""`GET /api/companies/{ticker}/quote` yanıtı — sayfa açılışında güncel fiyat.

Analiz anlık görüntüsünden (ADR-005) bağımsızdır: snapshot oluşturmaz,
yalnızca sağlayıcı başarısız olursa son snapshot'taki fiyata (`stale=True`)
düşer.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel


class LiveQuote(BaseModel):
    ticker: str
    price: float
    currency: str
    market_cap: float | None = None
    # Fiyatın zamanı: sağlayıcı borsa zamanını veriyorsa o, yoksa çekim anı;
    # `stale=True` ise snapshot'taki fiyatın zamanı.
    as_of: dt.datetime | None = None
    # Sağlayıcı kodu (ör. "yfinance"); yedek durumda "snapshot".
    source: str
    is_cached: bool = False
    stale: bool = False
    delay_note: str
    stale_note: str | None = None
    # Önceki kapanışa göre değişim — yalnızca sağlayıcı önceki kapanışı
    # veriyorsa (backend'de hesaplanır). `change_fraction` kesirdir: 0.012 == %1,2.
    previous_close: float | None = None
    change: float | None = None
    change_fraction: float | None = None
    direction: Literal["up", "down", "flat"] | None = None
