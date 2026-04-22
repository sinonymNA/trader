from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.clock import utcnow
from app.services.journaling import JournalService
from app.services.worker import WorkerState
from app.storage.repositories import TradeRepository

router = APIRouter(tags=["debug"])


def _default(obj: object) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


@router.get("/debug", response_class=JSONResponse)
async def debug(request: Request) -> JSONResponse:
    """
    Last computed feature snapshot for every instrument + recent journal.
    Copy-paste this to diagnose why the bot holds.
    """
    state: WorkerState = request.app.state.worker_state
    settings = request.app.state.settings
    day_limits = getattr(request.app.state, "day_limits", None)
    apex_sim = getattr(request.app.state, "apex_sim", None)
    journal: JournalService = request.app.state.journal

    journal_entries = await journal._repo.recent(limit=50)
    journal_data = [
        {
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "event_type": e.event_type,
            "instrument": e.instrument,
            "message": e.message,
        }
        for e in journal_entries
    ]

    payload: dict = {
        "generated_at": utcnow().isoformat(),
        "worker_status": state.status.value,
        "trading_enabled": settings.trading_enabled,
        "dry_run": settings.dry_run,
        "uptime_seconds": round(state.uptime_seconds, 1),
        "trades_today": day_limits.trades_today if day_limits else 0,
        "losses_today": day_limits.losses_today if day_limits else 0,
        "instruments_configured": settings.instrument_list(),
        "signal_snapshots": state.last_features,
        "apex": None,
        "recent_journal": journal_data,
    }

    if apex_sim is not None:
        can_trade, rule_status = apex_sim.check_rules()
        payload["apex"] = {
            "realized_pnl": apex_sim.realized_pnl,
            "daily_pnl": apex_sim.daily_pnl,
            "peak_balance": apex_sim.peak_balance,
            "can_trade": can_trade,
            "rule_status": rule_status,
        }

    return JSONResponse(content=json.loads(json.dumps(payload, default=_default)))


@router.get("/export", response_class=JSONResponse)
async def export(request: Request) -> JSONResponse:
    """Full data export — state + all trades + last 200 journal entries."""
    state: WorkerState = request.app.state.worker_state
    settings = request.app.state.settings
    trade_repo: TradeRepository = request.app.state.trade_repo
    journal: JournalService = request.app.state.journal

    trades = await trade_repo.list_all(limit=500)
    journal_entries = await journal._repo.recent(limit=200)

    trades_data = [
        {
            "id": t.id,
            "broker_trade_id": t.broker_trade_id,
            "instrument": t.instrument,
            "side": t.side,
            "units": t.units,
            "open_price": t.open_price,
            "close_price": t.close_price,
            "stop_loss": t.stop_loss,
            "take_profit": t.take_profit,
            "realized_pnl": t.realized_pnl,
            "status": t.status,
            "opened_at": t.opened_at.isoformat() if t.opened_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
        }
        for t in trades
    ]

    journal_data = [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "event_type": e.event_type,
            "instrument": e.instrument,
            "message": e.message,
        }
        for e in journal_entries
    ]

    payload = {
        "exported_at": utcnow().isoformat(),
        "worker_status": state.status.value,
        "trading_enabled": settings.trading_enabled,
        "dry_run": settings.dry_run,
        "signal_snapshots": state.last_features,
        "trades": trades_data,
        "journal": journal_data,
    }

    return JSONResponse(content=json.loads(json.dumps(payload, default=_default)))
