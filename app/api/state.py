from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.clock import is_market_open
from app.schemas.api import StateResponse
from app.services.worker import WorkerState

router = APIRouter(tags=["state"])


@router.get("/state", response_model=StateResponse)
async def get_state(request: Request) -> StateResponse:
    state: WorkerState = request.app.state.worker_state
    settings = request.app.state.settings
    return StateResponse(
        worker_status=state.status,
        dry_run=settings.dry_run,
        trading_enabled=settings.trading_enabled,
        uptime_seconds=state.uptime_seconds,
        market_open=is_market_open(settings.timezone),
        current_instrument=state.current_instrument,
        last_signal=state.last_signal,
        last_tick_at=state.last_tick_at,
    )
