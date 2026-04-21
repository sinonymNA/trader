from __future__ import annotations

from app.broker.oanda_client import OandaClient
from app.data.normalizers import normalize_candle
from app.schemas.domain import Candle


async def fetch_candles(
    client: OandaClient,
    instrument: str,
    granularity: str = "M5",
    count: int = 50,
) -> list[Candle]:
    raw = await client.get_candles(instrument, granularity, count)
    return [normalize_candle(c) for c in raw if c.get("complete", True)]
