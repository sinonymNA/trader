from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.clock import is_market_open
from app.schemas.api import ApexStateResponse, StateResponse
from app.services.worker import WorkerState

router = APIRouter(tags=["state"])


@router.get("/state", response_model=StateResponse)
async def get_state(request: Request) -> StateResponse:
    state: WorkerState = request.app.state.worker_state
    settings = request.app.state.settings
    day_limits = getattr(request.app.state, "day_limits", None)
    apex_sim = getattr(request.app.state, "apex_sim", None)

    apex_state: ApexStateResponse | None = None
    if apex_sim is not None:
        can_trade, rule_status = apex_sim.check_rules()
        apex_state = ApexStateResponse(
            realized_pnl=apex_sim.realized_pnl,
            daily_pnl=apex_sim.daily_pnl,
            peak_balance=apex_sim.peak_balance,
            current_balance=apex_sim.current_balance,
            can_trade=can_trade,
            rule_status=rule_status,
        )

    return StateResponse(
        worker_status=state.status,
        dry_run=settings.dry_run,
        trading_enabled=settings.trading_enabled,
        uptime_seconds=state.uptime_seconds,
        market_open=is_market_open(settings.timezone),
        current_instrument=state.current_instrument,
        last_signal=state.last_signal,
        last_tick_at=state.last_tick_at,
        trades_today=day_limits.trades_today if day_limits else 0,
        losses_today=day_limits.losses_today if day_limits else 0,
        apex_state=apex_state,
    )
