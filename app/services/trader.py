from __future__ import annotations

import logging

from app.core.clock import utcnow
from app.risk.limits import RiskLimits
from app.schemas.domain import OrderIntent, OrderResult
from app.services.journaling import JournalService
from app.storage.repositories import TradeRepository
from app.strategy.execution_policy import ExecutionPolicy

logger = logging.getLogger(__name__)


class Trader:
    """Orchestrates: risk check → execute → persist → journal."""

    def __init__(
        self,
        policy: ExecutionPolicy,
        risk: RiskLimits,
        trade_repo: TradeRepository,
        journal: JournalService,
        trading_enabled: bool = False,
    ) -> None:
        self._policy = policy
        self._risk = risk
        self._trade_repo = trade_repo
        self._journal = journal
        self._trading_enabled = trading_enabled

    async def execute(self, intent: OrderIntent) -> OrderResult | None:
        if not self._trading_enabled:
            logger.info(
                "TRADING_ENABLED=false — skipping %s %s",
                intent.side.value,
                intent.instrument,
            )
            await self._journal.record_event(
                "SKIPPED",
                f"Trading disabled; skipping {intent.side.value} {intent.instrument}",
                instrument=intent.instrument,
            )
            return None

        open_trades = await self._trade_repo.list_open()
        allowed, reason = self._risk.check_order(intent, open_trade_count=len(open_trades))
        if not allowed:
            logger.warning("Order blocked by risk limits: %s", reason)
            await self._journal.record_event(
                "RISK_REJECTED", reason, instrument=intent.instrument
            )
            return None

        result = await self._policy.execute(intent)
        if result.success:
            await self._trade_repo.create(result, opened_at=utcnow())
            await self._journal.record_fill(result)
            logger.info(
                "Trade opened: %s %s %d @ %.5f (order_id=%s)",
                result.side.value,
                result.instrument,
                result.units,
                result.fill_price,
                result.order_id,
            )
        else:
            logger.warning("Order failed: %s", result.error)
            await self._journal.record_error(result.error, instrument=intent.instrument)

        return result
