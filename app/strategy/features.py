from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.broker.oanda_client import OandaClient
from app.core.clock import utcnow
from app.data.candles import fetch_candles
from app.data.prices import fetch_prices
from app.schemas.domain import Candle, FeatureSet

logger = logging.getLogger(__name__)

_DEFAULT_MAX_CANDLE_AGE_SECONDS = 900  # 15 minutes


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _is_stale(candles: list[Candle], max_age_seconds: int) -> bool:
    if not candles:
        return False  # no candles → insufficient data (handled by MA check), not stale
    newest_time_str = candles[-1].time
    try:
        base = newest_time_str.split(".")[0]
        newest = datetime.fromisoformat(base + "+00:00")
        age = (datetime.now(timezone.utc) - newest).total_seconds()
        return age > max_age_seconds
    except (ValueError, AttributeError, IndexError):
        return False


async def build_feature_set(
    client: OandaClient,
    instrument: str,
    granularity: str = "M5",
    candle_count: int = 60,
    short_period: int = 10,
    long_period: int = 30,
    lookback: int = 20,
    max_candle_age_seconds: int = _DEFAULT_MAX_CANDLE_AGE_SECONDS,
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

    stale = _is_stale(candles, max_candle_age_seconds)
    closes = [c.close for c in candles]
    short_ma = _sma(closes, short_period)
    long_ma = _sma(closes, long_period)
    recent = closes[-lookback:] if len(closes) >= lookback else closes
    breakout_high = max(recent) if recent else None
    breakout_low = min(recent) if recent else None

    logger.debug(
        "Features %s: short_ma=%s long_ma=%s bh=%s bl=%s candles=%d stale=%s",
        instrument,
        f"{short_ma:.5f}" if short_ma is not None else "None",
        f"{long_ma:.5f}" if long_ma is not None else "None",
        f"{breakout_high:.5f}" if breakout_high is not None else "None",
        f"{breakout_low:.5f}" if breakout_low is not None else "None",
        len(candles),
        stale,
    )

    if stale:
        logger.warning("Stale candle data for %s (newest candle too old)", instrument)

    return FeatureSet(
        instrument=instrument,
        timestamp=utcnow(),
        mid_price=mid,
        spread=spread,
        candles=candles,
        short_ma=short_ma,
        long_ma=long_ma,
        breakout_high=breakout_high,
        breakout_low=breakout_low,
        stale=stale,
    )
