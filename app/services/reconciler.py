from __future__ import annotations

import logging

from app.broker.oanda_client import OandaClient
from app.storage.repositories import TradeRepository

logger = logging.getLogger(__name__)


class Reconciler:
    """
    Syncs open trades from OANDA against the local DB.

    TODO: implement full reconciliation logic:
      1. client.list_open_trades() → broker open trade IDs
      2. trade_repo.list_open() → DB open trade IDs
      3. Diff the two sets
      4. Close DB records for trades no longer open on broker
      5. Log discrepancies
    """

    def __init__(self, client: OandaClient, trade_repo: TradeRepository) -> None:
        self._client = client
        self._repo = trade_repo

    async def run(self) -> None:
        logger.debug("Reconciler.run() — stub, no action taken")
