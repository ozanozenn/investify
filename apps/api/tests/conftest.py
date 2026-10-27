"""Tüm testler için ortak ortam ayarları.

Bu dosya alt dizinlerdeki conftest'lerden ve `app.main` import edilmeden
önce yüklenir; `get_settings()` önbelleğe alındığı için ayarlar burada,
ilk çağrıdan önce verilmelidir.
"""

from __future__ import annotations

import os

# İzleme listesi zamanlayıcısı testlerde asla çalışmaz (ADR-013).
os.environ["WATCHLIST_REFRESH_ENABLED"] = "false"
