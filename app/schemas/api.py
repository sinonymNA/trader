from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.core.enums import WorkerStatus


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    dry_run: bool
    trading_enabled: bool
    version: str = "0.1.0"


class StateResponse(BaseModel):
    worker_status: WorkerStatus
    dry_run: bool
    trading_enabled: bool
    uptime_seconds: float
    market_open: bool
    current_instrument: str | None = None
    last_signal: str | None = None
    last_tick_at: datetime | None = None


class TradeResponse(BaseModel):
    id: str
    broker_trade_id: str
    instrument: str
    side: str
    units: int
    open_price: float
    close_price: float | None = None
    status: str
    opened_at: datetime
    closed_at: datetime | None = None

    model_config = {"from_attributes": True}


class TradesListResponse(BaseModel):
    trades: list[TradeResponse]
    count: int


class ControlResponse(BaseModel):
    ok: bool
    worker_status: WorkerStatus
    message: str
