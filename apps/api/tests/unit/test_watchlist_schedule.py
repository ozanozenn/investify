from __future__ import annotations

import asyncio
import datetime as dt

import pytest

from app.core.config import Settings, get_settings
from app.services.watchlist_scheduler import RefreshSchedule, WatchlistScheduler

UTC = dt.timezone.utc


def _weekday_schedule() -> RefreshSchedule:
    return RefreshSchedule.parse("mon-fri", "18:30", "Europe/Istanbul")


def test_parse_weekday_range_and_list():
    assert _weekday_schedule().weekdays == frozenset({0, 1, 2, 3, 4})
    assert RefreshSchedule.parse("mon,wed, fri", "09:00", "UTC").weekdays == frozenset({0, 2, 4})
    assert RefreshSchedule.parse("sat-sun", "09:00", "UTC").weekdays == frozenset({5, 6})


@pytest.mark.parametrize(
    ("days", "time"),
    [("", "18:30"), ("fri-mon", "18:30"), ("pzt", "18:30"), ("mon-fri", "25:00"), ("mon-fri", "1830")],
)
def test_parse_rejects_invalid_config(days, time):
    with pytest.raises(ValueError):
        RefreshSchedule.parse(days, time, "Europe/Istanbul")


def test_next_run_same_day_before_time():
    # Salı 12:00 İstanbul (09:00 UTC) -> aynı gün 18:30 İstanbul = 15:30 UTC
    now = dt.datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
    assert _weekday_schedule().next_run_after(now) == dt.datetime(2026, 10, 27, 15, 30, tzinfo=UTC)


def test_next_run_after_time_moves_to_next_day():
    now = dt.datetime(2026, 10, 27, 15, 30, tzinfo=UTC)  # tam o an: kesinlikle sonrası istenir
    assert _weekday_schedule().next_run_after(now) == dt.datetime(2026, 10, 28, 15, 30, tzinfo=UTC)


def test_next_run_skips_weekend():
    friday_evening = dt.datetime(2026, 10, 30, 17, 0, tzinfo=UTC)  # Cuma 20:00 İstanbul
    assert _weekday_schedule().next_run_after(friday_evening) == dt.datetime(2026, 11, 2, 15, 30, tzinfo=UTC)


def test_label_is_turkish():
    assert _weekday_schedule().label() == "Hafta içi her gün 18:30 (Europe/Istanbul)"
    assert RefreshSchedule.parse("mon,thu", "07:05", "UTC").label() == "Pazartesi, Perşembe 07:05 (UTC)"


def test_default_settings_enable_scheduler_after_bist_close():
    defaults = Settings(_env_file=None, watchlist_refresh_enabled=True)
    schedule = RefreshSchedule.from_settings(defaults)
    assert schedule.weekdays == frozenset(range(5))
    assert schedule.at == dt.time(18, 30)


def test_scheduler_disabled_in_tests():
    # tests/conftest.py WATCHLIST_REFRESH_ENABLED=false yapar.
    assert get_settings().watchlist_refresh_enabled is False


async def test_scheduler_loop_runs_job_at_slot_and_stops():
    target = dt.datetime.now(UTC) + dt.timedelta(milliseconds=150)
    schedule = RefreshSchedule(weekdays=frozenset(range(7)), at=target.time(), tz=UTC)
    calls: list[dt.datetime] = []
    fired = asyncio.Event()

    async def job(slot: dt.datetime) -> None:
        calls.append(slot)
        fired.set()

    scheduler = WatchlistScheduler(schedule, job, max_sleep_seconds=0.05)
    scheduler.start()
    assert scheduler.is_running
    await asyncio.wait_for(fired.wait(), timeout=3)
    assert calls[0] == target
    await scheduler.stop()
    assert not scheduler.is_running
    assert len(calls) == 1


async def test_scheduler_loop_survives_job_error():
    now = dt.datetime.now(UTC)
    schedule = RefreshSchedule(
        weekdays=frozenset(range(7)), at=(now + dt.timedelta(milliseconds=100)).time(), tz=UTC
    )
    fired = asyncio.Event()

    async def failing_job(slot: dt.datetime) -> None:
        fired.set()
        raise RuntimeError("boom")

    scheduler = WatchlistScheduler(schedule, failing_job, max_sleep_seconds=0.05)
    scheduler.start()
    await asyncio.wait_for(fired.wait(), timeout=3)
    await asyncio.sleep(0.05)
    assert scheduler.is_running  # hata döngüyü öldürmedi
    await scheduler.stop()
