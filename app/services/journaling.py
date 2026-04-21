from __future__ import annotations

import logging

from app.schemas.domain import OrderResult
from app.storage.repositories import JournalRepository

logger = logging.getLogger(__name__)


class JournalService:
    def __init__(self, repo: JournalRepository) -> None:
        self._repo = repo

    async def record_event(
        self,
        event_type: str,
        message: str,
        instrument: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        logger.debug("journal [%s] %s", event_type, message)
        await self._repo.append(
            event_type=event_type,
            message=message,
            instrument=instrument,
            metadata=metadata,
        )

    async def record_fill(self, result: OrderResult) -> None:
        await self._repo.append(
            event_type="ORDER_FILLED",
            message=(
                f"{result.side.value} {result.units} {result.instrument} "
                f"@ {result.fill_price:.5f}"
            ),
            instrument=result.instrument,
            metadata={
                "order_id": result.order_id,
                "fill_price": result.fill_price,
                "dry_run": result.dry_run,
            },
        )

    async def record_error(
        self, message: str, instrument: str | None = None
    ) -> None:
        logger.error("journal error: %s", message)
        await self._repo.append(
            event_type="ERROR",
            message=message,
            instrument=instrument,
        )
