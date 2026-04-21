from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.schemas.domain import ApexSimulator, OrderIntent, OrderResult

if TYPE_CHECKING:
    from app.broker.oanda_client import OandaClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# APEX_SIMULATOR_HOOK
#
# To plug in an Apex-challenge simulator instead of sending real orders:
#
#   from app.schemas.domain import ApexSimulator, OrderIntent, OrderResult
#
#   class MyApexSim:
#       async def simulate_order(self, intent: OrderIntent) -> OrderResult:
#           # Enforce Apex rules: daily loss limit, max drawdown, profit target,
#           # minimum trading days, consistency requirements.
#           return OrderResult(success=True, order_id="APEX-123", ...)
#
#   policy = ExecutionPolicy(
#       client=oanda_client,
#       max_units=1000,
#       simulator=MyApexSim(),   # <-- inject here
#   )
#
# When a simulator is present, execute() routes through it instead of OANDA.
# ---------------------------------------------------------------------------


class ExecutionPolicy:
    """Maps OrderIntent → OrderResult via broker or Apex simulator."""

    def __init__(
        self,
        client: "OandaClient",
        max_units: int = 1000,
        simulator: ApexSimulator | None = None,
    ) -> None:
        self._client = client
        self._max_units = max_units
        self._simulator = simulator

    async def execute(self, intent: OrderIntent) -> OrderResult:
        if self._simulator is not None:
            logger.info(
                "Routing order through Apex simulator: %s %s %d",
                intent.side.value,
                intent.instrument,
                intent.units,
            )
            return await self._simulator.simulate_order(intent)

        signed_units = (
            intent.units if intent.side.value == "BUY" else -intent.units
        )
        raw = await self._client.place_market_order(
            intent.instrument,
            signed_units,
            stop_loss=intent.stop_loss,
            take_profit=intent.take_profit,
        )
        fill = raw.get("orderFillTransaction", {})

        return OrderResult(
            success=True,
            order_id=fill.get("id", "UNKNOWN"),
            instrument=intent.instrument,
            side=intent.side,
            units=abs(int(fill.get("units", intent.units))),
            fill_price=float(fill.get("price", 0.0)),
            dry_run=self._client._dry_run,
        )
