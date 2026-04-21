from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ApexSimulatorPolicy:
    """
    Implements Apex Funding Challenge rules as a standalone policy object.

    Tracks realized PnL, peak balance, and daily stats. Call check_rules()
    before placing any order; call on_fill() after each closed trade.

    Challenge states:
      - can_trade=True  → challenge still active, within all limits
      - can_trade=False, reason="Daily loss limit"    → failed for the day
      - can_trade=False, reason="Trailing drawdown"   → challenge failed permanently
      - can_trade=False, reason="Profit target reached" → challenge passed!
    """

    def __init__(
        self,
        account_size: float = 100_000.0,
        max_daily_loss_pct: float = 0.02,
        max_trailing_drawdown_pct: float = 0.04,
        profit_target_pct: float = 0.08,
    ) -> None:
        self._account_size = account_size
        self._max_daily_loss_pct = max_daily_loss_pct
        self._max_trailing_drawdown_pct = max_trailing_drawdown_pct
        self._profit_target_pct = profit_target_pct

        self._realized_pnl: float = 0.0
        self._peak_balance: float = account_size
        self._daily_start_balance: float = account_size
        self._day: int = datetime.now(timezone.utc).day

        logger.info(
            "ApexSimulatorPolicy initialized: account_size=%.0f "
            "max_daily_loss=%.1f%% trailing_dd=%.1f%% profit_target=%.1f%%",
            account_size,
            max_daily_loss_pct * 100,
            max_trailing_drawdown_pct * 100,
            profit_target_pct * 100,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @property
    def _current_balance(self) -> float:
        return self._account_size + self._realized_pnl

    def _maybe_reset_daily(self) -> None:
        today = datetime.now(timezone.utc).day
        if today != self._day:
            logger.info(
                "ApexSim: new UTC day — resetting daily start balance "
                "(was %.2f, now %.2f)",
                self._daily_start_balance,
                self._current_balance,
            )
            self._daily_start_balance = self._current_balance
            self._day = today

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_rules(self) -> tuple[bool, str]:
        """
        Returns (can_trade, reason).
        can_trade=False means the challenge has ended (pass or fail).
        """
        self._maybe_reset_daily()
        current = self._current_balance

        daily_loss = self._daily_start_balance - current
        max_daily_loss = self._account_size * self._max_daily_loss_pct
        if daily_loss >= max_daily_loss:
            return False, (
                f"Daily loss limit hit: lost ${daily_loss:.2f} "
                f"(limit ${max_daily_loss:.2f})"
            )

        trailing_drawdown = self._peak_balance - current
        max_trailing_dd = self._account_size * self._max_trailing_drawdown_pct
        if trailing_drawdown >= max_trailing_dd:
            return False, (
                f"Trailing drawdown limit hit: ${trailing_drawdown:.2f} "
                f"from peak ${self._peak_balance:.2f} "
                f"(limit ${max_trailing_dd:.2f})"
            )

        profit = self._realized_pnl
        profit_target = self._account_size * self._profit_target_pct
        if profit >= profit_target:
            return False, (
                f"Profit target reached! PnL=${profit:.2f} "
                f"(target ${profit_target:.2f})"
            )

        return True, "OK"

    def on_fill(self, pnl: float) -> None:
        """Record realized PnL from a closed trade and update peak balance."""
        self._realized_pnl += pnl
        self._peak_balance = max(self._peak_balance, self._current_balance)
        logger.info(
            "ApexSim: trade closed pnl=%.4f  total_pnl=%.4f  peak=%.2f  current=%.2f",
            pnl,
            self._realized_pnl,
            self._peak_balance,
            self._current_balance,
        )

    def reset_daily(self) -> None:
        """Manually reset daily stats (e.g. at market open)."""
        self._daily_start_balance = self._current_balance
        self._day = datetime.now(timezone.utc).day

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    @property
    def realized_pnl(self) -> float:
        return self._realized_pnl

    @property
    def peak_balance(self) -> float:
        return self._peak_balance

    @property
    def current_balance(self) -> float:
        return self._current_balance

    @property
    def daily_pnl(self) -> float:
        self._maybe_reset_daily()
        return self._current_balance - self._daily_start_balance
