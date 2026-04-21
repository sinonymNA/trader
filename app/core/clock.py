from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
import zoneinfo


_now_fn: Callable[[], datetime] | None = None


def utcnow() -> datetime:
    if _now_fn is not None:
        return _now_fn()
    return datetime.now(tz=timezone.utc)


def now_in_tz(tz: str) -> datetime:
    zone = zoneinfo.ZoneInfo(tz)
    return utcnow().astimezone(zone)


def is_market_open(tz: str = "America/New_York") -> bool:
    """Heuristic forex hours: Sunday 17:00 ET → Friday 17:00 ET."""
    local = now_in_tz(tz)
    weekday = local.weekday()  # 0=Mon, 6=Sun
    hour = local.hour

    if weekday == 5:  # Saturday
        return False
    if weekday == 6:  # Sunday
        return hour >= 17
    if weekday == 4:  # Friday
        return hour < 17
    return True  # Mon–Thu always open


def seconds_since(dt: datetime) -> float:
    return (utcnow() - dt).total_seconds()


def override_now(fn: Callable[[], datetime] | None) -> None:
    """Test helper — pass None to restore the real clock."""
    global _now_fn
    _now_fn = fn
