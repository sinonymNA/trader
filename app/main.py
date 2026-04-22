from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api import control, dashboard, health, state, trades
from app.broker.oanda_client import OandaClient
from app.config import get_settings
from app.core.logging import configure_logging
from app.risk.day_limits import DayLimits
from app.risk.kill_switch import KillSwitch
from app.risk.limits import RiskLimits
from app.services.journaling import JournalService
from app.services.reconciler import Reconciler
from app.services.trader import Trader
from app.services.worker import Worker, WorkerState
from app.storage.db import dispose_engine, init_db, get_session_factory
from app.storage.repositories import JournalRepository, TradeRepository
from app.strategy.apex_simulator import ApexSimulatorPolicy
from app.strategy.execution_policy import ExecutionPolicy
from app.strategy.signal_engine import SignalEngine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging(settings.log_level)

    logger.info(
        "Starting oanda-apex-bot  DRY_RUN=%s  TRADING_ENABLED=%s",
        settings.dry_run,
        settings.trading_enabled,
    )

    if not settings.dry_run:
        settings.validate_for_live()
        # Build a temporary client just to verify credentials before starting
        _check_client = OandaClient(
            api_key=settings.oanda_api_key,
            account_id=settings.oanda_account_id,
            base_url=settings.oanda_base_url,
            dry_run=False,
        )
        try:
            await _check_client.verify()
        except RuntimeError as exc:
            logger.critical("OANDA credential check failed: %s", exc)
            await _check_client.close()
            raise
        await _check_client.close()

    # Storage
    await init_db(settings.database_url)
    session_factory = get_session_factory(settings.database_url)
    trade_repo = TradeRepository(session_factory)
    journal_repo = JournalRepository(session_factory)

    # Broker
    oanda_client = OandaClient(
        api_key=settings.oanda_api_key,
        account_id=settings.oanda_account_id,
        base_url=settings.oanda_base_url,
        dry_run=settings.dry_run,
    )

    # Apex simulator (optional funded-challenge rule engine)
    apex_sim: ApexSimulatorPolicy | None = None
    if settings.apex_enabled:
        apex_sim = ApexSimulatorPolicy(
            account_size=settings.apex_account_size,
            max_daily_loss_pct=settings.apex_max_daily_loss_pct,
            max_trailing_drawdown_pct=settings.apex_trailing_drawdown_pct,
            profit_target_pct=settings.apex_profit_target_pct,
        )
        logger.info("Apex simulator ENABLED")

    # Strategy + Risk
    signal_engine = SignalEngine(trade_units=settings.trade_units)
    policy = ExecutionPolicy(
        client=oanda_client,
        max_units=settings.max_position_units,
        apex_sim=apex_sim,
    )
    risk = RiskLimits(
        max_position_units=settings.max_position_units,
        max_open_trades=settings.max_open_trades,
        daily_loss_limit_usd=settings.daily_loss_limit_usd,
    )
    kill_switch = KillSwitch()
    day_limits = DayLimits(
        max_trades_per_day=settings.max_trades_per_day,
        max_losses_per_day=settings.max_losses_per_day,
    )
    journal = JournalService(journal_repo)
    trader = Trader(
        policy=policy,
        risk=risk,
        trade_repo=trade_repo,
        journal=journal,
        trading_enabled=settings.trading_enabled,
        day_limits=day_limits,
    )
    reconciler = Reconciler(oanda_client, trade_repo, day_limits=day_limits, apex_sim=apex_sim)

    # Shared state
    worker_state = WorkerState()

    # Wire into app.state for API routes
    app.state.worker_state = worker_state
    app.state.trade_repo = trade_repo
    app.state.settings = settings
    app.state.day_limits = day_limits
    app.state.apex_sim = apex_sim
    app.state.client = oanda_client
    app.state.journal = journal

    # Background worker
    worker = Worker(
        state=worker_state,
        client=oanda_client,
        trader=trader,
        journal=journal,
        kill_switch=kill_switch,
        reconciler=reconciler,
        signal_engine=signal_engine,
        policy=policy,
        instruments=settings.instrument_list(),
        interval_seconds=settings.worker_interval_seconds,
        timezone=settings.timezone,
        stop_loss_pips=settings.stop_loss_pips,
        take_profit_pips=settings.take_profit_pips,
        candle_granularity="M5",
        candle_count=settings.candle_count,
        short_ma_period=settings.short_ma_period,
        long_ma_period=settings.long_ma_period,
        breakout_lookback=settings.breakout_lookback,
    )
    worker_task = asyncio.create_task(worker.run(), name="trading-worker")

    yield  # ← app is live

    logger.info("Shutting down...")
    worker_state.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    await oanda_client.close()
    await dispose_engine()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="oanda-apex-bot",
        version="0.1.0",
        description=(
            "Autonomous forex practice-trading bot with OANDA v20 API integration "
            "and Apex-style simulator seam."
        ),
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(state.router)
    app.include_router(trades.router)
    app.include_router(control.router)
    app.include_router(dashboard.router)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/dashboard")

    return app


app = create_app()
