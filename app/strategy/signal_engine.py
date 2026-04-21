from __future__ import annotations

import logging

from app.core.enums import Side, SignalStrength
from app.core.clock import utcnow
from app.schemas.domain import FeatureSet, Signal

logger = logging.getLogger(__name__)


class SignalEngine:
    """
    Placeholder signal engine — always returns None (no trade).

    Replace the body of evaluate() with real strategy logic:
      - SMA/EMA crossover from FeatureSet.candles
      - RSI, MACD, Bollinger bands
      - Spread filter to avoid wide-spread entries

    Returns Signal when a trade should be placed, None to hold.
    """

    def evaluate(self, features: FeatureSet) -> Signal | None:
        if not features.candles:
            logger.debug(
                "No candles for %s, holding", features.instrument
            )
            return None

        # STUB: no signal. Replace with real logic below.
        logger.debug(
            "SignalEngine stub: %s mid=%.5f spread=%.5f → HOLD",
            features.instrument,
            features.mid_price,
            features.spread,
        )
        return None
