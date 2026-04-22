from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from app.core.clock import is_market_open, utcnow
from app.core.enums import WorkerStatus
from app.risk.kill_switch import KillSwitch
from app.services.journaling import JournalService
from app.services.reconciler import Reconciler
from app.services.trader import Trader
from app.strategy.execution_policy import ExecutionPolicy
from app.strategy.features import build_feature_set
from app.strategy.signal_engine import SignalEngine
from app.broker.oanda_client import OandaClient
from app.schemas.domain import OrderIntent

logger = logging.getLogger(__name__)


class WorkerState:
    """
    Shared mutable state between the async worker loop and the API layer.
    All reads/writes happen on the single asyncio event loop — no locks needed.
    """

    def __init__(self) -> None:
        self._paused: bool = False
        self.killed: bool = False
        self.started_at: datetime = utcnow()
        self.current_instrument: str | None = None
        self.last_signal: str | None = None
        self.last_tick_at: datetime | None = None
        # Keyed by instrument — stores last evaluated feature snapshot for /debug
        self.last_features: dict[str, dict] = {}
        # Account snapshot — refreshed each tick from OANDA
        self.account_balance: float | None = None
        self.account_nav: float | None = None
        self.account_unrealized_pnl: float | None = None
        self.account_open_trade_count: int | None = None

    @property
    def is_paused(self) -> bool:
        return self._paused

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self.killed = True

    @property
    def status(self) -> WorkerStatus:
        if self.killed:
            return WorkerStatus.STOPPED
        if self._paused:
            return WorkerStatus.PAUSED
        return WorkerStatus.RUNNING

    @property
    def uptime_seconds(self) -> float:
        return (utcnow() - self.started_at).total_seconds()


class Worker:
    def __init__(
        self,
        state: WorkerState,
        client: OandaClient,
        trader: Trader,
        journal: JournalService,
        kill_switch: KillSwitch,
        reconciler: Reconciler,
        signal_engine: SignalEngine,
        policy: ExecutionPolicy,
        instruments: list[str],
        interval_seconds: int = 15,
        timezone: str = "America/New_York",
        stop_loss_pips: float = 20.0,
        take_profit_pips: float = 40.0,
        candle_granularity: str = "M5",
        candle_count: int = 60,
        short_ma_period: int = 10,
        long_ma_period: int = 30,
        breakout_lookback: int = 20,
    ) -> None:
        self._state = state
        self._client = client
        self._trader = trader
        self._journal = journal
        self._kill_switch = kill_switch
        self._reconciler = reconciler
        self._signal_engine = signal_engine
        self._policy = policy
        self._instruments = instruments
        self._interval = interval_seconds
        self._timezone = timezone
        self._stop_loss_pips = stop_loss_pips
        self._take_profit_pips = take_profit_pips
        self._candle_granularity = candle_granularity
        self._candle_count = candle_count
        self._short_ma_period = short_ma_period
        self._long_ma_period = long_ma_period
        self._breakout_lookback = breakout_lookback

    async def run(self) -> None:
        logger.info(
            "Worker starting. instruments=%s interval=%ds",
            self._instruments,
            self._interval,
        )
        await self._journal.record_event("WORKER_STARTED", "Worker loop started")

        while not self._state.killed:
            if self._state.is_paused:
                await asyncio.sleep(1)
                continue

            if not is_market_open(self._timezone):
                logger.debug("Market closed, sleeping 60s")
                await asyncio.sleep(60)
                continue

            try:
                await self._tick()
                self._kill_switch.record_success()
            except Exception as exc:
                logger.exception("Worker tick error: %s", exc)
                self._kill_switch.record_error()
                await self._journal.record_error(f"Tick error: {exc}")

            should_kill, reason = self._kill_switch.should_kill()
            if should_kill:
                logger.critical("Kill switch triggered: %s", reason)
                await self._journal.record_event("KILL_SWITCH", reason)
                self._state.stop()
                break

            await asyncio.sleep(self._interval)

        logger.warning("Worker loop exited. killed=%s", self._state.killed)

    async def _tick(self) -> None:
        cycle_at = utcnow()
        self._state.last_tick_at = cycle_at
        logger.info("── Tick @ %s ──", cycle_at.strftime("%Y-%m-%dT%H:%M:%SZ"))

        # Account summary — fail-soft so a transient error doesn't abort the tick
        try:
            summary = await self._client.get_account_summary()
            acct = summary.get("account", {})
            self._state.account_balance = float(acct.get("balance", 0) or 0)
            self._state.account_nav = float(acct.get("NAV", 0) or 0)
            self._state.account_unrealized_pnl = float(acct.get("unrealizedPL", 0) or 0)
            self._state.account_open_trade_count = int(acct.get("openTradeCount", 0) or 0)
            logger.info(
                "Account  balance=%s  NAV=%s  unrealizedPL=%s  openTrades=%s",
                self._state.account_balance,
                self._state.account_nav,
                self._state.account_unrealized_pnl,
                self._state.account_open_trade_count,
            )
        except Exception as exc:
            logger.warning("Could not fetch account summary: %s", exc)

        await self._reconciler.run()

        for instrument in self._instruments:
            self._state.current_instrument = instrument

            features = await build_feature_set(
                self._client,
                instrument,
                granularity=self._candle_granularity,
                candle_count=self._candle_count,
                short_period=self._short_ma_period,
                long_period=self._long_ma_period,
                lookback=self._breakout_lookback,
            )

            bid = features.mid_price - features.spread / 2
            ask = features.mid_price + features.spread / 2
            logger.info(
                "Price  %-10s  bid=%.5f  ask=%.5f  spread=%.5f  candles=%d",
                instrument,
                bid,
                ask,
                features.spread,
                len(features.candles),
            )

            signal = self._signal_engine.evaluate(features)

            # Determine hold reason for diagnostics
            if signal is None:
                if features.stale:
                    hold_reason = "stale data"
                elif features.short_ma is None or features.long_ma is None:
                    hold_reason = "insufficient candle data for MA"
                elif features.breakout_high is None or features.breakout_low is None:
                    hold_reason = "insufficient candle data for breakout"
                else:
                    max_spread = 0.05 if "JPY" in instrument else 0.0005
                    if features.spread > max_spread:
                        hold_reason = f"spread {features.spread:.5f} > limit {max_spread}"
                    elif features.short_ma > features.long_ma:
                        hold_reason = f"MA bullish but price {features.mid_price:.5f} ≤ breakout_high {features.breakout_high:.5f}"
                    elif features.short_ma < features.long_ma:
                        hold_reason = f"MA bearish but price {features.mid_price:.5f} ≥ breakout_low {features.breakout_low:.5f}"
                    else:
                        hold_reason = "MAs flat / no crossover"
            else:
                hold_reason = None

            # Store snapshot for /debug endpoint
            self._state.last_features[instrument] = {
                "instrument": instrument,
                "mid_price": features.mid_price,
                "spread": features.spread,
                "short_ma": features.short_ma,
                "long_ma": features.long_ma,
                "breakout_high": features.breakout_high,
                "breakout_low": features.breakout_low,
                "candle_count": len(features.candles),
                "stale": features.stale,
                "signal": signal.side.value if signal else "HOLD",
                "hold_reason": hold_reason,
                "evaluated_at": utcnow().isoformat(),
            }

            if signal is None:
                self._state.last_signal = "HOLD"
                logger.info("Signal %-10s → HOLD (%s)", instrument, hold_reason)
                await self._journal.record_event("SIGNAL", "HOLD", instrument=instrument)
                continue

            logger.info(
                "Signal %-10s → %s (%s)  reason=%s",
                instrument,
                signal.side.value,
                signal.strength.value,
                signal.reason,
            )
            self._state.last_signal = signal.side.value
            await self._journal.record_event(
                "SIGNAL",
                f"{signal.side.value} ({signal.strength.value}) — {signal.reason}",
                instrument=instrument,
            )

            # Compute absolute SL/TP prices from pip config
            pip = 0.01 if "JPY" in instrument else 0.0001
            decimals = 3 if "JPY" in instrument else 5
            if signal.side.value == "BUY":
                sl = round(features.mid_price - self._stop_loss_pips * pip, decimals)
                tp = round(features.mid_price + self._take_profit_pips * pip, decimals)
            else:
                sl = round(features.mid_price + self._stop_loss_pips * pip, decimals)
                tp = round(features.mid_price - self._take_profit_pips * pip, decimals)

            logger.info(
                "Order  %-10s  %s  units=%d  SL=%s  TP=%s",
                instrument,
                signal.side.value,
                signal.units,
                sl,
                tp,
            )

            intent = OrderIntent(
                instrument=signal.instrument,
                side=signal.side,
                units=signal.units,
                stop_loss=sl,
                take_profit=tp,
            )
            await self._trader.execute(intent)
