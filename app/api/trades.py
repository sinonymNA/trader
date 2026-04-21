from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.api import TradeResponse, TradesListResponse
from app.schemas.domain import TradeRecord
from app.storage.repositories import TradeRepository

router = APIRouter(tags=["trades"])


def _to_response(record: TradeRecord) -> TradeResponse:
    return TradeResponse(
        id=record.id,
        broker_trade_id=record.broker_trade_id,
        instrument=record.instrument,
        side=record.side,
        units=record.units,
        open_price=record.open_price,
        close_price=record.close_price,
        status=record.status,
        opened_at=record.opened_at,
        closed_at=record.closed_at,
    )


@router.get("/trades", response_model=TradesListResponse)
async def list_trades(request: Request) -> TradesListResponse:
    repo: TradeRepository = request.app.state.trade_repo
    trades = await repo.list_all(limit=100)
    return TradesListResponse(
        trades=[_to_response(t) for t in trades],
        count=len(trades),
    )
