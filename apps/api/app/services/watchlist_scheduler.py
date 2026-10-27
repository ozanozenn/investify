"""İzleme listesi için süreç içi zamanlayıcı (ADR-013).

APScheduler yerine küçük bir asyncio döngüsü: tek bir "hafta içi SS:DD"
kuralı için yeni bağımlılık, iş deposu veya misfire ayarı gerekmiyor.
Döngü uzun bekleyişleri en fazla `max_sleep_seconds`'lık parçalara böler ve
her uyanışta duvar saatine yeniden bakar; böylece makine uykusu ya da saat
düzeltmesi zamanlamayı kaydırmaz.

Bilinen sınır: sunucu planlanan anda kapalıysa o çalıştırma sonradan
telafi edilmez; bir sonraki zaman diliminde çalışır.
"""

from __future__ import annotations

import asyncio
import datetime as dt
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.base import utcnow

logger = get_logger(__name__)

_DAY_CODES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_DAY_LABELS_TR = ("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar")


def _parse_days(spec: str) -> frozenset[int]:
    days: set[int] = set()
    for part in (p.strip().lower() for p in spec.split(",")):
        if not part:
            continue
        if "-" in part:
            start_code, end_code = (s.strip() for s in part.split("-", 1))
            if start_code not in _DAY_CODES or end_code not in _DAY_CODES:
                raise ValueError(f"Geçersiz gün aralığı: {part!r}")
            start, end = _DAY_CODES.index(start_code), _DAY_CODES.index(end_code)
            if start > end:
                raise ValueError(f"Gün aralığı ters: {part!r}")
            days.update(range(start, end + 1))
        elif part in _DAY_CODES:
            days.add(_DAY_CODES.index(part))
        else:
            raise ValueError(f"Geçersiz gün: {part!r}")
    if not days:
        raise ValueError("En az bir gün belirtilmeli")
    return frozenset(days)


def _parse_time(spec: str) -> dt.time:
    try:
        hour_str, minute_str = spec.strip().split(":")
        return dt.time(int(hour_str), int(minute_str))
    except ValueError as exc:
        raise ValueError(f"Geçersiz saat (SS:DD bekleniyor): {spec!r}") from exc


@dataclass(frozen=True)
class RefreshSchedule:
    weekdays: frozenset[int]  # 0 = Pazartesi
    at: dt.time
    tz: dt.tzinfo

    @classmethod
    def parse(cls, days: str, time: str, tz_name: str) -> RefreshSchedule:
        return cls(weekdays=_parse_days(days), at=_parse_time(time), tz=ZoneInfo(tz_name))

    @classmethod
    def from_settings(cls, settings: Settings) -> RefreshSchedule:
        return cls.parse(settings.watchlist_refresh_days, settings.watchlist_refresh_time, settings.timezone)

    def next_run_after(self, now: dt.datetime) -> dt.datetime:
        """`now`dan kesinlikle sonraki ilk çalıştırma anı (UTC)."""
        local_now = now.astimezone(self.tz)
        for offset in range(8):
            day = local_now.date() + dt.timedelta(days=offset)
            if day.weekday() not in self.weekdays:
                continue
            candidate = dt.datetime.combine(day, self.at, tzinfo=self.tz)
            if candidate > local_now:
                return candidate.astimezone(dt.timezone.utc)
        raise RuntimeError("Zamanlama boş — en az bir gün olmalı")  # parse() bunu engeller

    def label(self) -> str:
        days = sorted(self.weekdays)
        if days == list(range(5)):
            day_text = "Hafta içi her gün"
        elif days == list(range(7)):
            day_text = "Her gün"
        else:
            day_text = ", ".join(_DAY_LABELS_TR[d] for d in days)
        return f"{day_text} {self.at.strftime('%H:%M')} ({self.tz})"


Job = Callable[[dt.datetime], Awaitable[object]]


class WatchlistScheduler:
    """Zamanı gelince `job(slot)`'u çağıran tek görevli döngü. `slot`,
    çalıştırmanın planlandığı an (UTC) — iş tekrarını önlemek için kullanılır."""

    def __init__(
        self,
        schedule: RefreshSchedule,
        job: Job,
        *,
        now_fn: Callable[[], dt.datetime] = utcnow,
        max_sleep_seconds: float = 300.0,
    ) -> None:
        self.schedule = schedule
        self._job = job
        self._now = now_fn
        self._max_sleep = max_sleep_seconds
        self._task: asyncio.Task | None = None
        self.next_run_at: dt.datetime | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        if self.is_running:
            return
        self.next_run_at = self.schedule.next_run_after(self._now())
        self._task = asyncio.create_task(self._loop(), name="watchlist-scheduler")
        logger.info(
            "watchlist_scheduler_started",
            extra={"schedule": self.schedule.label(), "next_run_at": self.next_run_at.isoformat()},
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        self.next_run_at = None

    async def _loop(self) -> None:
        while True:
            slot = self.schedule.next_run_after(self._now())
            self.next_run_at = slot
            while (remaining := (slot - self._now()).total_seconds()) > 0:
                await asyncio.sleep(min(remaining, self._max_sleep))
            try:
                await self._job(slot)
            except Exception:  # döngü bir hatada ölmemeli
                logger.exception("watchlist_scheduled_job_failed", extra={"slot": slot.isoformat()})
