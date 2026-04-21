from __future__ import annotations

import logging

from app.core.clock import utcnow
from app.core.enums import Side, SignalStrength
from app.schemas.domain import FeatureSet, Signal

logger = logging.getLogger(__name__)

_MAX_SPREAD_DEFAULT = 0.0005   # 5 pips for non-JPY pairs
_MAX_SPREAD_JPY = 0.05         # 5 pips for JPY pairs (pip = 0.01)


class SignalEngine:
    """
    MA-crossover + breakout signal engine.

    BUY  when short_MA > long_MA  AND  mid_price > breakout_high
    SELL when short_MA < long_MA  AND  mid_price < breakout_low
    HOLD otherwise (or when data is insufficient / spread too wide)
    """

    def __init__(self, trade_units: int = 100) -> None:
        self._trade_units = trade_units

    def evaluate(self, features: FeatureSet) -> Signal | None:
        if features.stale:
            logger.debug("Stale data for %s, holding", features.instrument)
            return None

        if features.short_ma is None or features.long_ma is None:
            logger.debug("Insufficient MA data for %s, holding", features.instrument)
            return None

        if features.breakout_high is None or features.breakout_low is None:
            logger.debug("Insufficient breakout data for %s, holding", features.instrument)
            return None

        max_spread = (
            _MAX_SPREAD_JPY if "JPY" in features.instrument else _MAX_SPREAD_DEFAULT
        )
        if features.spread > max_spread:
            logger.debug(
                "Spread too wide for %s (%.5f > %.5f), holding",
                features.instrument,
                features.spread,
                max_spread,
            )
            return None

        ma_bull = features.short_ma > features.long_ma
        ma_bear = features.short_ma < features.long_ma
        price_above_breakout = features.mid_price > features.breakout_high
        price_below_breakout = features.mid_price < features.breakout_low

        if ma_bull and price_above_breakout:
            reason = (
                f"short_ma({features.short_ma:.5f}) > long_ma({features.long_ma:.5f})"
                f" AND price({features.mid_price:.5f}) > bh({features.breakout_high:.5f})"
            )
            logger.info("BUY signal %s: %s", features.instrument, reason)
            return Signal(
                instrument=features.instrument,
                side=Side.BUY,
                strength=SignalStrength.MODERATE,
                units=self._trade_units,
                reason=reason,
                generated_at=utcnow(),
            )

        if ma_bear and price_below_breakout:
            reason = (
                f"short_ma({features.short_ma:.5f}) < long_ma({features.long_ma:.5f})"
                f" AND price({features.mid_price:.5f}) < bl({features.breakout_low:.5f})"
            )
            logger.info("SELL signal %s: %s", features.instrument, reason)
            return Signal(
                instrument=features.instrument,
                side=Side.SELL,
                strength=SignalStrength.MODERATE,
                units=self._trade_units,
                reason=reason,
                generated_at=utcnow(),
            )

        logger.debug(
            "Hold %s: ma_bull=%s price_above=%s ma_bear=%s price_below=%s",
            features.instrument,
            ma_bull,
            price_above_breakout,
            ma_bear,
            price_below_breakout,
        )
        return None
