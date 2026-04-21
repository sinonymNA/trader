"""
Unit tests for ApexSimulatorPolicy — funded challenge rule engine.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.strategy.apex_simulator import ApexSimulatorPolicy


def _sim(
    account_size: float = 100_000.0,
    max_daily_loss_pct: float = 0.02,
    max_trailing_drawdown_pct: float = 0.04,
    profit_target_pct: float = 0.08,
) -> ApexSimulatorPolicy:
    return ApexSimulatorPolicy(
        account_size=account_size,
        max_daily_loss_pct=max_daily_loss_pct,
        max_trailing_drawdown_pct=max_trailing_drawdown_pct,
        profit_target_pct=profit_target_pct,
    )


def test_can_trade_initially() -> None:
    sim = _sim()
    ok, reason = sim.check_rules()
    assert ok is True
    assert reason == "OK"


def test_blocks_when_daily_loss_limit_hit() -> None:
    sim = _sim(account_size=100_000.0, max_daily_loss_pct=0.02)
    sim.on_fill(-2_000.0)  # exactly at limit
    ok, reason = sim.check_rules()
    assert ok is False
    assert "daily loss" in reason.lower()


def test_blocks_when_trailing_drawdown_hit() -> None:
    # Use high daily loss pct so it doesn't trigger before trailing drawdown
    sim = _sim(
        account_size=100_000.0,
        max_daily_loss_pct=0.10,
        max_trailing_drawdown_pct=0.04,
    )
    sim.on_fill(2_000.0)   # peak rises to 102_000
    sim.on_fill(-6_000.0)  # drawdown from peak: 6_000 > 4_000 limit
    ok, reason = sim.check_rules()
    assert ok is False
    assert "trailing drawdown" in reason.lower()


def test_blocks_when_profit_target_reached() -> None:
    sim = _sim(account_size=100_000.0, profit_target_pct=0.08)
    sim.on_fill(8_000.0)
    ok, reason = sim.check_rules()
    assert ok is False
    assert "profit target" in reason.lower()


def test_peak_balance_updates_after_winning_trade() -> None:
    sim = _sim(account_size=100_000.0)
    assert sim.peak_balance == 100_000.0
    sim.on_fill(1_500.0)
    assert sim.peak_balance == 101_500.0
    sim.on_fill(-500.0)
    assert sim.peak_balance == 101_500.0  # peak doesn't decrease


def test_daily_reset_allows_trading_again() -> None:
    sim = _sim(account_size=100_000.0, max_daily_loss_pct=0.02)
    sim.on_fill(-2_000.0)
    ok, _ = sim.check_rules()
    assert ok is False

    # Simulate a new UTC day
    tomorrow_day = (sim._day % 31) + 1
    with patch("app.strategy.apex_simulator.datetime") as mock_dt:
        from datetime import timezone
        mock_dt.now.return_value = __import__("datetime").datetime(
            2024, 1, tomorrow_day, 0, 0, tzinfo=timezone.utc
        )
        sim.reset_daily()
        ok_after, reason = sim.check_rules()
    # After reset, daily loss is 0 but trailing drawdown may still block
    # With loss of 2000 (within 4% trailing dd limit), should be tradeable
    assert ok_after is True


def test_realized_pnl_and_current_balance() -> None:
    sim = _sim(account_size=100_000.0)
    sim.on_fill(500.0)
    sim.on_fill(-200.0)
    assert sim.realized_pnl == 300.0
    assert sim.current_balance == 100_300.0


def test_daily_pnl_tracks_intraday_moves() -> None:
    sim = _sim(account_size=100_000.0)
    assert sim.daily_pnl == 0.0
    sim.on_fill(1_000.0)
    assert sim.daily_pnl == 1_000.0
    sim.on_fill(-300.0)
    assert sim.daily_pnl == 700.0
