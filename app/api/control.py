from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.clock import utcnow
from app.schemas.api import ControlResponse
from app.services.worker import WorkerState

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/control", tags=["control"])


class FlattenResponse(BaseModel):
    ok: bool
    closed_count: int
    closed_trade_ids: list[str]
    message: str


@router.post("/pause", response_model=ControlResponse)
async def pause(request: Request) -> ControlResponse:
    state: WorkerState = request.app.state.worker_state
    if state.killed:
        return ControlResponse(
            ok=False,
            worker_status=state.status,
            message="Worker is stopped and cannot be paused",
        )
    state.pause()
    return ControlResponse(
        ok=True,
        worker_status=state.status,
        message="Worker paused",
    )


@router.post("/resume", response_model=ControlResponse)
async def resume(request: Request) -> ControlResponse:
    state: WorkerState = request.app.state.worker_state
    if state.killed:
        return ControlResponse(
            ok=False,
            worker_status=state.status,
            message="Worker is stopped and cannot be resumed",
        )
    state.resume()
    return ControlResponse(
        ok=True,
        worker_status=state.status,
        message="Worker resumed",
    )


@router.post("/flatten", response_model=FlattenResponse)
async def flatten(request: Request) -> FlattenResponse:
    """Close all open trades immediately."""
    trade_repo = request.app.state.trade_repo
    client = request.app.state.client
    journal = request.app.state.journal

    open_trades = await trade_repo.list_open()
    closed_ids: list[str] = []

    for trade in open_trades:
        try:
            raw = await client.close_trade(trade.broker_trade_id)
            fill = raw.get("orderFillTransaction", {})
            close_price = float(fill.get("price", 0.0))
            await trade_repo.close_with_pnl(
                broker_trade_id=trade.broker_trade_id,
                close_price=close_price,
                realized_pnl=0.0,
                closed_at=utcnow(),
            )
            await journal.record_event(
                "FLATTEN",
                f"Manually closed trade {trade.broker_trade_id}",
                instrument=trade.instrument,
            )
            closed_ids.append(trade.broker_trade_id)
            logger.info("Flatten: closed trade %s", trade.broker_trade_id)
        except Exception as exc:
            logger.error("Flatten: failed to close trade %s: %s", trade.broker_trade_id, exc)

    return FlattenResponse(
        ok=True,
        closed_count=len(closed_ids),
        closed_trade_ids=closed_ids,
        message=f"Flattened {len(closed_ids)} trade(s)",
    )


@router.post("/toggle-trading", response_model=ControlResponse)
async def toggle_trading(request: Request) -> ControlResponse:
    """Toggle trading_enabled at runtime."""
    state: WorkerState = request.app.state.worker_state
    settings = request.app.state.settings
    settings.trading_enabled = not settings.trading_enabled
    status = "enabled" if settings.trading_enabled else "disabled"
    logger.info("Trading %s via /control/toggle-trading", status)
    return ControlResponse(
        ok=True,
        worker_status=state.status,
        message=f"Trading {status}",
    )
