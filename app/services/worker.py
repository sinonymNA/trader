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
        interval_seconds: int = 30,
        timezone: str = "America/New_York",
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
        await self._reconciler.run()
        self._state.last_tick_at = utcnow()

        for instrument in self._instruments:
            self._state.current_instrument = instrument

            features = await build_feature_set(self._client, instrument)
            signal = self._signal_engine.evaluate(features)

            if signal is None:
                self._state.last_signal = "HOLD"
                await self._journal.record_event(
                    "SIGNAL", "HOLD", instrument=instrument
                )
                continue

            self._state.last_signal = signal.side.value
            await self._journal.record_event(
                "SIGNAL",
                f"{signal.side.value} ({signal.strength.value}) — {signal.reason}",
                instrument=instrument,
            )

            intent = OrderIntent(
                instrument=signal.instrument,
                side=signal.side,
                units=signal.units,
            )
            await self._trader.execute(intent)
