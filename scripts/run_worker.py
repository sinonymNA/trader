#!/usr/bin/env python3
"""
Standalone worker entry point — runs the trading loop without the API server.
Useful for running the worker and API as separate processes.
"""
import asyncio
import logging

from app.broker.oanda_client import OandaClient
from app.config import get_settings
from app.core.logging import configure_logging
from app.risk.kill_switch import KillSwitch
from app.risk.limits import RiskLimits
from app.services.journaling import JournalService
from app.services.reconciler import Reconciler
from app.services.trader import Trader
from app.services.worker import Worker, WorkerState
from app.storage.db import dispose_engine, get_session_factory, init_db
from app.storage.repositories import JournalRepository, TradeRepository
from app.strategy.execution_policy import ExecutionPolicy
from app.strategy.signal_engine import SignalEngine


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    if not settings.dry_run:
        settings.validate_for_live()

    await init_db(settings.database_url)
    factory = get_session_factory(settings.database_url)
    trade_repo = TradeRepository(factory)
    journal_repo = JournalRepository(factory)
    journal = JournalService(journal_repo)

    client = OandaClient(
        api_key=settings.oanda_api_key,
        account_id=settings.oanda_account_id,
        base_url=settings.oanda_base_url,
        dry_run=settings.dry_run,
    )
    policy = ExecutionPolicy(client=client, max_units=settings.max_position_units)
    risk = RiskLimits(
        max_position_units=settings.max_position_units,
        daily_loss_limit_usd=settings.daily_loss_limit_usd,
    )
    kill_switch = KillSwitch()
    trader = Trader(
        policy=policy,
        risk=risk,
        trade_repo=trade_repo,
        journal=journal,
        trading_enabled=settings.trading_enabled,
    )
    reconciler = Reconciler(client, trade_repo)
    signal_engine = SignalEngine()
    worker_state = WorkerState()

    worker = Worker(
        state=worker_state,
        client=client,
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

    logger.info(
        "Worker starting  DRY_RUN=%s  TRADING_ENABLED=%s",
        settings.dry_run,
        settings.trading_enabled,
    )
    try:
        await worker.run()
    finally:
        await client.close()
        await dispose_engine()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
