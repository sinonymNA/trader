from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.api import control, health, state, trades
from app.broker.oanda_client import OandaClient
from app.config import get_settings
from app.core.logging import configure_logging
from app.risk.kill_switch import KillSwitch
from app.risk.limits import RiskLimits
from app.services.journaling import JournalService
from app.services.reconciler import Reconciler
from app.services.trader import Trader
from app.services.worker import Worker, WorkerState
from app.storage.db import dispose_engine, init_db, get_session_factory
from app.storage.repositories import JournalRepository, TradeRepository
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

    # Strategy + Risk
    signal_engine = SignalEngine()
    policy = ExecutionPolicy(client=oanda_client, max_units=settings.max_position_units)
    risk = RiskLimits(
        max_position_units=settings.max_position_units,
        daily_loss_limit_usd=settings.daily_loss_limit_usd,
    )
    kill_switch = KillSwitch()
    journal = JournalService(journal_repo)
    trader = Trader(
        policy=policy,
        risk=risk,
        trade_repo=trade_repo,
        journal=journal,
        trading_enabled=settings.trading_enabled,
    )
    reconciler = Reconciler(oanda_client, trade_repo)

    # Shared state
    worker_state = WorkerState()

    # Wire into app.state for API routes
    app.state.worker_state = worker_state
    app.state.trade_repo = trade_repo
    app.state.settings = settings

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
    return app


app = create_app()
