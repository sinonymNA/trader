from __future__ import annotations

from app.broker.oanda_client import OandaClient
from app.core.clock import utcnow
from app.data.candles import fetch_candles
from app.data.prices import fetch_prices
from app.schemas.domain import FeatureSet


async def build_feature_set(
    client: OandaClient,
    instrument: str,
    granularity: str = "M5",
    candle_count: int = 50,
) -> FeatureSet:
    prices = await fetch_prices(client, [instrument])
    candles = await fetch_candles(client, instrument, granularity, candle_count)

    if prices:
        p = prices[0]
        mid = p.mid
        spread = p.spread
    else:
        mid = 0.0
        spread = 0.0

    return FeatureSet(
        instrument=instrument,
        timestamp=utcnow(),
        mid_price=mid,
        spread=spread,
        candles=candles,
    )
