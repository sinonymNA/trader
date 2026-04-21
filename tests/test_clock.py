from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.clock import is_market_open, override_now, utcnow


def teardown_function():
    override_now(None)


def test_utcnow_is_tz_aware() -> None:
    now = utcnow()
    assert now.tzinfo is not None


def test_utcnow_is_utc() -> None:
    now = utcnow()
    # UTC offset must be zero
    assert now.utcoffset().total_seconds() == 0


def test_override_now_replaces_clock() -> None:
    fixed = datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
    override_now(lambda: fixed)
    assert utcnow() == fixed


def test_override_none_restores_real_clock() -> None:
    fixed = datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
    override_now(lambda: fixed)
    override_now(None)
    assert utcnow() != fixed  # real clock is different


def test_market_open_wednesday_noon() -> None:
    # Wednesday 2024-06-05 14:00 UTC = 10:00 ET — market open
    fixed = datetime(2024, 6, 5, 14, 0, 0, tzinfo=timezone.utc)
    override_now(lambda: fixed)
    assert is_market_open("America/New_York") is True


def test_market_closed_saturday() -> None:
    # Saturday 2024-06-01
    fixed = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    override_now(lambda: fixed)
    assert is_market_open("America/New_York") is False


def test_market_closed_sunday_morning() -> None:
    # Sunday 2024-06-02 10:00 UTC = 06:00 ET — before 17:00 open
    fixed = datetime(2024, 6, 2, 10, 0, 0, tzinfo=timezone.utc)
    override_now(lambda: fixed)
    assert is_market_open("America/New_York") is False


def test_market_open_sunday_evening() -> None:
    # Sunday 2024-06-02 23:00 UTC = 19:00 ET — after 17:00 open
    fixed = datetime(2024, 6, 2, 23, 0, 0, tzinfo=timezone.utc)
    override_now(lambda: fixed)
    assert is_market_open("America/New_York") is True


def test_market_closed_friday_evening() -> None:
    # Friday 2024-06-07 22:00 UTC = 18:00 ET — after 17:00 close
    fixed = datetime(2024, 6, 7, 22, 0, 0, tzinfo=timezone.utc)
    override_now(lambda: fixed)
    assert is_market_open("America/New_York") is False
