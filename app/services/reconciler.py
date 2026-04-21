from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.broker.oanda_client import OandaClient
from app.core.clock import utcnow
from app.risk.day_limits import DayLimits
from app.storage.repositories import TradeRepository

if TYPE_CHECKING:
    from app.strategy.apex_simulator import ApexSimulatorPolicy

logger = logging.getLogger(__name__)


class Reconciler:
    """
    Syncs open trades from OANDA against the local DB.

    On each call:
    1. Fetches open trade IDs from the broker.
    2. Compares against DB records with status=OPEN.
    3. For any trade that disappeared from the broker, fetches final details
       and closes the DB record with realized PnL.
    4. Records losses against DayLimits if PnL is negative.
    5. Notifies ApexSimulatorPolicy of realized PnL via on_fill().

    Skipped entirely in dry-run mode without credentials (broker always returns []).
    """

    def __init__(
        self,
        client: OandaClient,
        trade_repo: TradeRepository,
        day_limits: DayLimits | None = None,
        apex_sim: "ApexSimulatorPolicy | None" = None,
    ) -> None:
        self._client = client
        self._repo = trade_repo
        self._day_limits = day_limits
        self._apex_sim = apex_sim

    async def run(self) -> None:
        if self._client._dry_run and not self._client._has_credentials():
            logger.debug("Reconciler: dry-run without credentials — skipping")
            return

        try:
            broker_trades = await self._client.list_open_trades()
        except Exception as exc:
            logger.warning("Reconciler: failed to fetch broker trades: %s", exc)
            return

        broker_ids = {t["id"] for t in broker_trades}
        db_open = await self._repo.list_open()

        for trade in db_open:
            if trade.broker_trade_id in broker_ids:
                continue

            # Trade is closed on the broker side — fetch final details
            close_price = 0.0
            realized_pnl = 0.0
            try:
                detail = await self._client.get_trade(trade.broker_trade_id)
                trade_data = detail.get("trade", {})
                close_price = float(trade_data.get("closeoutPrice", 0.0))
                realized_pnl = float(trade_data.get("realizedPL", 0.0))
            except Exception as exc:
                logger.warning(
                    "Reconciler: could not fetch details for trade %s: %s",
                    trade.broker_trade_id,
                    exc,
                )

            await self._repo.close_with_pnl(
                broker_trade_id=trade.broker_trade_id,
                close_price=close_price,
                realized_pnl=realized_pnl,
                closed_at=utcnow(),
            )

            logger.info(
                "Reconciler: closed trade %s  pnl=%.4f  close_price=%.5f",
                trade.broker_trade_id,
                realized_pnl,
                close_price,
            )

            if self._day_limits and realized_pnl < 0:
                self._day_limits.record_loss()

            if self._apex_sim is not None:
                self._apex_sim.on_fill(realized_pnl)
