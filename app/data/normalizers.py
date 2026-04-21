from __future__ import annotations

from app.schemas.domain import Candle, Price


def normalize_candle(raw: dict) -> Candle:
    mid = raw.get("mid", {})
    return Candle(
        time=raw.get("time", ""),
        open=float(mid.get("o", 0)),
        high=float(mid.get("h", 0)),
        low=float(mid.get("l", 0)),
        close=float(mid.get("c", 0)),
        volume=int(raw.get("volume", 0)),
        complete=bool(raw.get("complete", True)),
    )


def normalize_price(raw: dict) -> Price:
    asks = raw.get("asks", [])
    bids = raw.get("bids", [])
    ask = float(asks[0]["price"]) if asks else 0.0
    bid = float(bids[0]["price"]) if bids else 0.0
    return Price(
        instrument=raw.get("instrument", ""),
        bid=bid,
        ask=ask,
        time=raw.get("time", ""),
    )
