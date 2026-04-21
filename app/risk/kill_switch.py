from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class KillSwitch:
    """
    Hard-stop mechanism. Once triggered, the worker loop terminates.

    Extend should_kill() with drawdown calculations, consecutive error counts,
    broker connectivity failures, etc.
    """

    def __init__(self, max_consecutive_errors: int = 5) -> None:
        self._max_consecutive_errors = max_consecutive_errors
        self._error_count: int = 0
        self._triggered: bool = False
        self._reason: str = ""

    def record_error(self) -> None:
        self._error_count += 1
        logger.warning(
            "Kill switch error count: %d/%d",
            self._error_count,
            self._max_consecutive_errors,
        )

    def record_success(self) -> None:
        self._error_count = 0

    def trigger(self, reason: str) -> None:
        self._triggered = True
        self._reason = reason
        logger.critical("Kill switch triggered: %s", reason)

    def reset(self) -> None:
        self._triggered = False
        self._error_count = 0
        self._reason = ""

    def should_kill(self) -> tuple[bool, str]:
        if self._triggered:
            return True, self._reason
        if self._error_count >= self._max_consecutive_errors:
            reason = f"Consecutive error threshold reached ({self._error_count})"
            return True, reason
        return False, ""
