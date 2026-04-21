from __future__ import annotations

from app.broker.oanda_client import OandaClient
from app.data.normalizers import normalize_price
from app.schemas.domain import Price


async def fetch_prices(
    client: OandaClient,
    instruments: list[str],
) -> list[Price]:
    raw = await client.get_latest_prices(instruments)
    return [normalize_price(p) for p in raw]
