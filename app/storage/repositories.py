from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.ids import new_trade_id, new_journal_id
from app.schemas.domain import OrderResult, TradeRecord
from app.storage.models import JournalEntryModel, TradeModel


def _model_to_record(m: TradeModel) -> TradeRecord:
    return TradeRecord(
        id=m.id,
        broker_trade_id=m.broker_trade_id,
        instrument=m.instrument,
        side=m.side,
        units=m.units,
        open_price=m.open_price,
        close_price=m.close_price,
        status=m.status,
        opened_at=m.opened_at,
        closed_at=m.closed_at,
    )


class TradeRepository:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def create(self, result: OrderResult, opened_at: datetime) -> TradeRecord:
        async with self._factory() as session:
            model = TradeModel(
                id=new_trade_id(),
                broker_trade_id=result.order_id,
                instrument=result.instrument,
                side=result.side.value,
                units=result.units,
                open_price=result.fill_price,
                status="OPEN",
                opened_at=opened_at,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return _model_to_record(model)

    async def get(self, trade_id: str) -> TradeRecord | None:
        async with self._factory() as session:
            result = await session.execute(
                select(TradeModel).where(TradeModel.id == trade_id)
            )
            model = result.scalar_one_or_none()
            return _model_to_record(model) if model else None

    async def list_open(self) -> list[TradeRecord]:
        async with self._factory() as session:
            result = await session.execute(
                select(TradeModel).where(TradeModel.status == "OPEN")
            )
            return [_model_to_record(r) for r in result.scalars().all()]

    async def list_all(self, limit: int = 100) -> list[TradeRecord]:
        async with self._factory() as session:
            result = await session.execute(
                select(TradeModel).order_by(TradeModel.opened_at.desc()).limit(limit)
            )
            return [_model_to_record(r) for r in result.scalars().all()]

    async def close(
        self,
        broker_trade_id: str,
        close_price: float,
        closed_at: datetime,
    ) -> TradeRecord | None:
        async with self._factory() as session:
            result = await session.execute(
                select(TradeModel).where(TradeModel.broker_trade_id == broker_trade_id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                return None
            model.close_price = close_price
            model.closed_at = closed_at
            model.status = "CLOSED"
            await session.commit()
            await session.refresh(model)
            return _model_to_record(model)


class JournalRepository:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def append(
        self,
        event_type: str,
        message: str,
        instrument: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        async with self._factory() as session:
            entry = JournalEntryModel(
                id=new_journal_id(),
                timestamp=datetime.utcnow(),
                event_type=event_type,
                instrument=instrument,
                message=message,
                metadata_json=json.dumps(metadata) if metadata else None,
            )
            session.add(entry)
            await session.commit()

    async def recent(self, limit: int = 50) -> list[JournalEntryModel]:
        async with self._factory() as session:
            result = await session.execute(
                select(JournalEntryModel)
                .order_by(JournalEntryModel.timestamp.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
