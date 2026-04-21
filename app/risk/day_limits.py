from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class DayLimits:
    """
    Tracks per-day trade and loss counts; auto-resets at UTC midnight.
    Thread-safe for single asyncio event loop (no locks needed).
    """

    def __init__(self, max_trades_per_day: int = 3, max_losses_per_day: int = 2) -> None:
        self._max_trades = max_trades_per_day
        self._max_losses = max_losses_per_day
        self._trades_today: int = 0
        self._losses_today: int = 0
        self._day: int = datetime.now(timezone.utc).day

    def _maybe_reset(self) -> None:
        today = datetime.now(timezone.utc).day
        if today != self._day:
            logger.info(
                "DayLimits: UTC day rolled over — resetting counts "
                "(trades_today=%d losses_today=%d)",
                self._trades_today,
                self._losses_today,
            )
            self._trades_today = 0
            self._losses_today = 0
            self._day = today

    def can_trade(self, open_trade_count: int = 0) -> tuple[bool, str]:
        self._maybe_reset()
        if self._trades_today >= self._max_trades:
            return False, (
                f"Daily trade limit reached ({self._trades_today}/{self._max_trades})"
            )
        if self._losses_today >= self._max_losses:
            return False, (
                f"Daily loss limit reached ({self._losses_today}/{self._max_losses})"
            )
        return True, "OK"

    def record_trade(self) -> None:
        self._maybe_reset()
        self._trades_today += 1
        logger.info(
            "DayLimits: trade recorded (trades_today=%d/%d)",
            self._trades_today,
            self._max_trades,
        )

    def record_loss(self) -> None:
        self._maybe_reset()
        self._losses_today += 1
        logger.info(
            "DayLimits: loss recorded (losses_today=%d/%d)",
            self._losses_today,
            self._max_losses,
        )

    @property
    def trades_today(self) -> int:
        self._maybe_reset()
        return self._trades_today

    @property
    def losses_today(self) -> int:
        self._maybe_reset()
        return self._losses_today
