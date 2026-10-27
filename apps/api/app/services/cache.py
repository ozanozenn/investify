"""Hafif JSON önbelleği (Redis, TTL'li).

Önbellek bir hızlandırıcıdır, doğruluk kaynağı değildir: Redis'e
ulaşılamazsa bir kez uyarı loglanır ve servis "önbellek yokmuş gibi"
davranır — hiçbir istek önbellek yüzünden başarısız olmaz. Kesinti
sırasında her istekte bağlantı zaman aşımı ödememek için kısa bir süre
(`retry_after_seconds`) Redis hiç denenmez, sonra yeniden denenir.
"""

from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any, Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_CONNECT_TIMEOUT_SECONDS = 0.5
_RETRY_AFTER_SECONDS = 30.0


class JsonCache(Protocol):
    async def get_json(self, key: str) -> Any | None: ...

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None: ...


class NullCache:
    """`cache_enabled=False` için: hiçbir şey saklamaz."""

    async def get_json(self, key: str) -> Any | None:
        return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        return None


class RedisJsonCache:
    def __init__(
        self,
        url: str,
        *,
        client: Redis | None = None,
        retry_after_seconds: float = _RETRY_AFTER_SECONDS,
    ) -> None:
        self._url = url
        self._client = client
        self._retry_after_seconds = retry_after_seconds
        self._down_until = 0.0
        self._outage_logged = False

    def _redis(self) -> Redis:
        if self._client is None:
            self._client = Redis.from_url(
                self._url,
                socket_connect_timeout=_CONNECT_TIMEOUT_SECONDS,
                socket_timeout=_CONNECT_TIMEOUT_SECONDS,
                decode_responses=True,
            )
        return self._client

    def _skipping(self) -> bool:
        return time.monotonic() < self._down_until

    def _mark_down(self, exc: BaseException) -> None:
        self._down_until = time.monotonic() + self._retry_after_seconds
        if not self._outage_logged:
            self._outage_logged = True
            logger.warning(
                "cache_unavailable",
                extra={"error": f"{type(exc).__name__}: {exc}", "fallback": "no-cache"},
            )

    def _mark_up(self) -> None:
        if self._outage_logged:
            self._outage_logged = False
            logger.info("cache_recovered")

    async def get_json(self, key: str) -> Any | None:
        if self._skipping():
            return None
        try:
            raw = await self._redis().get(key)
        except (RedisError, OSError, TimeoutError) as exc:
            self._mark_down(exc)
            return None
        self._mark_up()
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            logger.warning("cache_entry_unreadable", extra={"key": key})
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        if self._skipping():
            return
        payload = json.dumps(value, ensure_ascii=False)
        try:
            await self._redis().set(key, payload, ex=max(1, int(ttl_seconds)))
        except (RedisError, OSError, TimeoutError) as exc:
            self._mark_down(exc)
            return
        self._mark_up()


@lru_cache
def get_cache() -> JsonCache:
    """Süreç başına tek önbellek istemcisi (FastAPI bağımlılığı)."""
    settings = get_settings()
    if not settings.cache_enabled:
        return NullCache()
    return RedisJsonCache(settings.redis_url)
