from __future__ import annotations

import logging

from app.schemas.domain import OrderIntent

logger = logging.getLogger(__name__)


class RiskLimits:
    """Pre-trade risk checks."""

    def __init__(
        self,
        max_position_units: int = 1000,
        max_open_trades: int = 3,
        daily_loss_limit_usd: float = 50.0,
    ) -> None:
        self.max_position_units = max_position_units
        self.max_open_trades = max_open_trades
        self.daily_loss_limit_usd = daily_loss_limit_usd
        self._realized_loss_today: float = 0.0

    def record_loss(self, loss_usd: float) -> None:
        if loss_usd > 0:
            self._realized_loss_today += loss_usd
            logger.info("Daily realized loss: $%.2f", self._realized_loss_today)

    def reset_daily(self) -> None:
        self._realized_loss_today = 0.0

    def check_order(
        self,
        intent: OrderIntent,
        open_trade_count: int = 0,
    ) -> tuple[bool, str]:
        """Return (allowed, reason). allowed=True means the order may proceed."""
        if intent.units > self.max_position_units:
            return False, (
                f"units {intent.units} exceeds max_position_units {self.max_position_units}"
            )
        if open_trade_count >= self.max_open_trades:
            return False, (
                f"open trade count {open_trade_count} >= max_open_trades {self.max_open_trades}"
            )
        if self._realized_loss_today >= self.daily_loss_limit_usd:
            return False, (
                f"daily loss limit ${self.daily_loss_limit_usd:.2f} reached "
                f"(current: ${self._realized_loss_today:.2f})"
            )
        return True, ""
