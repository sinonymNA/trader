"""
Tests for the autonomous trading strategy components:
  - DayLimits (trade/loss counting with daily reset)
  - SignalEngine (MA-crossover + breakout logic)
  - RiskLimits (single-open-trade enforcement)
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.core.enums import Side, SignalStrength
from app.risk.day_limits import DayLimits
from app.risk.limits import RiskLimits
from app.schemas.domain import FeatureSet, OrderIntent
from app.strategy.signal_engine import SignalEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_features(
    mid_price: float = 1.10000,
    spread: float = 0.00020,
    short_ma: float | None = None,
    long_ma: float | None = None,
    breakout_high: float | None = None,
    breakout_low: float | None = None,
    stale: bool = False,
    instrument: str = "EUR_USD",
) -> FeatureSet:
    return FeatureSet(
        instrument=instrument,
        timestamp=datetime.now(timezone.utc),
        mid_price=mid_price,
        spread=spread,
        short_ma=short_ma,
        long_ma=long_ma,
        breakout_high=breakout_high,
        breakout_low=breakout_low,
        stale=stale,
    )


# ---------------------------------------------------------------------------
# DayLimits tests
# ---------------------------------------------------------------------------


def test_day_limits_can_trade_initially() -> None:
    dl = DayLimits(max_trades_per_day=3, max_losses_per_day=2)
    ok, reason = dl.can_trade()
    assert ok is True
    assert reason == "OK"


def test_day_limits_blocks_after_max_trades() -> None:
    dl = DayLimits(max_trades_per_day=2, max_losses_per_day=5)
    dl.record_trade()
    dl.record_trade()
    ok, reason = dl.can_trade()
    assert ok is False
    assert "trade limit" in reason.lower()


def test_day_limits_blocks_after_max_losses() -> None:
    dl = DayLimits(max_trades_per_day=10, max_losses_per_day=2)
    dl.record_loss()
    dl.record_loss()
    ok, reason = dl.can_trade()
    assert ok is False
    assert "loss limit" in reason.lower()


def test_day_limits_trades_today_count() -> None:
    dl = DayLimits(max_trades_per_day=5, max_losses_per_day=5)
    assert dl.trades_today == 0
    dl.record_trade()
    dl.record_trade()
    assert dl.trades_today == 2


def test_day_limits_losses_today_count() -> None:
    dl = DayLimits(max_trades_per_day=5, max_losses_per_day=5)
    assert dl.losses_today == 0
    dl.record_loss()
    assert dl.losses_today == 1


def test_day_limits_resets_on_new_day() -> None:
    dl = DayLimits(max_trades_per_day=2, max_losses_per_day=2)
    dl.record_trade()
    dl.record_trade()
    dl.record_loss()
    assert dl.trades_today == 2
    assert dl.losses_today == 1

    # Simulate a new UTC day
    tomorrow_day = (dl._day % 31) + 1  # wrap around month boundary safely
    with patch("app.risk.day_limits.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, tomorrow_day, 0, 0, tzinfo=timezone.utc)
        assert dl.trades_today == 0
        assert dl.losses_today == 0
        ok, _ = dl.can_trade()
        assert ok is True


# ---------------------------------------------------------------------------
# SignalEngine tests
# ---------------------------------------------------------------------------


def test_signal_engine_returns_buy_on_bullish_crossover() -> None:
    engine = SignalEngine(trade_units=100)
    features = _make_features(
        mid_price=1.10100,
        short_ma=1.10050,
        long_ma=1.09900,
        breakout_high=1.10000,
        breakout_low=1.09800,
    )
    signal = engine.evaluate(features)
    assert signal is not None
    assert signal.side == Side.BUY
    assert signal.units == 100
    assert signal.strength == SignalStrength.MODERATE


def test_signal_engine_returns_sell_on_bearish_crossover() -> None:
    engine = SignalEngine(trade_units=50)
    features = _make_features(
        mid_price=1.09700,
        short_ma=1.09800,
        long_ma=1.10000,
        breakout_high=1.10200,
        breakout_low=1.09750,
    )
    signal = engine.evaluate(features)
    assert signal is not None
    assert signal.side == Side.SELL
    assert signal.units == 50


def test_signal_engine_hold_when_mas_not_crossed() -> None:
    engine = SignalEngine()
    features = _make_features(
        mid_price=1.10000,
        short_ma=1.09950,
        long_ma=1.10050,  # short < long → bearish MA
        breakout_high=1.10100,
        breakout_low=1.09800,
        # price NOT below breakout_low → no sell signal
    )
    signal = engine.evaluate(features)
    assert signal is None


def test_signal_engine_hold_when_no_ma_data() -> None:
    engine = SignalEngine()
    features = _make_features(short_ma=None, long_ma=None)
    assert engine.evaluate(features) is None


def test_signal_engine_hold_when_no_breakout_data() -> None:
    engine = SignalEngine()
    features = _make_features(
        short_ma=1.10050,
        long_ma=1.09900,
        breakout_high=None,
        breakout_low=None,
    )
    assert engine.evaluate(features) is None


def test_signal_engine_hold_on_wide_spread() -> None:
    engine = SignalEngine()
    features = _make_features(
        spread=0.0010,  # 10 pips — too wide
        short_ma=1.10050,
        long_ma=1.09900,
        breakout_high=1.10000,
        breakout_low=1.09800,
    )
    assert engine.evaluate(features) is None


def test_signal_engine_hold_on_stale_data() -> None:
    engine = SignalEngine()
    features = _make_features(
        stale=True,
        short_ma=1.10050,
        long_ma=1.09900,
        breakout_high=1.10000,
        breakout_low=1.09800,
    )
    assert engine.evaluate(features) is None


def test_signal_engine_jpy_spread_filter() -> None:
    engine = SignalEngine()
    # Spread of 0.04 is ok for JPY (max is 0.05)
    features = _make_features(
        instrument="USD_JPY",
        mid_price=148.000,
        spread=0.04,
        short_ma=148.100,
        long_ma=147.900,
        breakout_high=147.950,
        breakout_low=147.700,
    )
    signal = engine.evaluate(features)
    assert signal is not None
    assert signal.side == Side.BUY

    # But spread of 0.06 is too wide
    features_wide = _make_features(
        instrument="USD_JPY",
        mid_price=148.000,
        spread=0.06,
        short_ma=148.100,
        long_ma=147.900,
        breakout_high=147.950,
        breakout_low=147.700,
    )
    assert engine.evaluate(features_wide) is None


# ---------------------------------------------------------------------------
# RiskLimits — single open trade enforcement
# ---------------------------------------------------------------------------


def test_risk_limits_blocks_second_open_trade() -> None:
    risk = RiskLimits(max_position_units=1000, max_open_trades=1)
    intent = OrderIntent(instrument="EUR_USD", side=Side.BUY, units=100)
    ok, _ = risk.check_order(intent, open_trade_count=1)
    assert ok is False


def test_risk_limits_allows_when_no_open_trades() -> None:
    risk = RiskLimits(max_position_units=1000, max_open_trades=1)
    intent = OrderIntent(instrument="EUR_USD", side=Side.BUY, units=100)
    ok, _ = risk.check_order(intent, open_trade_count=0)
    assert ok is True


def test_risk_limits_blocks_oversized_units() -> None:
    risk = RiskLimits(max_position_units=500, max_open_trades=3)
    intent = OrderIntent(instrument="EUR_USD", side=Side.BUY, units=501)
    ok, reason = risk.check_order(intent, open_trade_count=0)
    assert ok is False
    assert "501" in reason
