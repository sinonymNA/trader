# AGENTS.md — Developer & AI Extension Guide

## Overview

This repo implements a production-style autonomous forex trading bot. The architecture is designed to be extended safely — new strategies, simulators, and risk rules can be added without touching the core worker loop.

## Directory Map

```
app/
  api/           FastAPI routes (health, state, trades, control, dashboard)
  broker/        OANDA v20 async HTTP client (dry-run aware, retry/backoff)
  core/          Clock, enums, IDs, logging
  data/          OANDA response normalizers (candles, prices)
  risk/          RiskLimits, KillSwitch, DayLimits
  schemas/       Pydantic API models + domain dataclasses
  services/      Worker loop, Trader orchestrator, Reconciler, Journaling
  storage/       SQLAlchemy models + async repositories
  strategy/      SignalEngine, features.py, ExecutionPolicy, ApexSimulatorPolicy
scripts/
  run_api.py     Uvicorn entrypoint
  run_worker.py  Standalone worker entrypoint
tests/           pytest suite (asyncio_mode = auto)
```

## Key Extension Points

### 1. Add a New Signal Strategy

Edit `app/strategy/signal_engine.py`:
- `SignalEngine.evaluate(features: FeatureSet) → Signal | None`
- Return a `Signal` with `side`, `strength`, `units`, `reason`
- Return `None` to hold

Add new computed fields to `FeatureSet` (in `app/schemas/domain.py`) and compute them in `app/strategy/features.py :: build_feature_set()`.

### 2. Apex Simulator Seam

`app/strategy/apex_simulator.py` implements funded-challenge rules:
- `check_rules()` — call before placing an order; returns `(can_trade, reason)`
- `on_fill(pnl)` — call after a trade closes; updates peak balance and realized PnL

Enable via `APEX_ENABLED=true` and configure with `APEX_ACCOUNT_SIZE`, `APEX_MAX_DAILY_LOSS_PCT`, etc.

To inject a completely custom Apex simulator (replacing order routing):
1. Implement the `ApexSimulator` Protocol from `app/schemas/domain.py`
2. Pass `simulator=MyApexSim()` to `ExecutionPolicy(...)` in `app/main.py`

### 3. Add a New Instrument

Add to `INSTRUMENTS` env var (comma-separated). Instruments with `JPY` in the name automatically use 3 decimal place pricing and a wider spread threshold.

### 4. New Risk Rule

Add a check in `app/risk/limits.py :: RiskLimits.check_order()` or `app/risk/day_limits.py :: DayLimits.can_trade()`. Both are called by `app/services/trader.py` before placing orders.

### 5. New API Endpoint

Add a file to `app/api/`, create a `router = APIRouter(...)`, and register it in `app/main.py :: create_app()`.

### 6. Dashboard Customization

The dashboard is a single inline HTML string in `app/api/dashboard.py`. It polls `/state` and `/trades` every 5 seconds via vanilla JS `fetch()`. Extend by adding fields to the API responses and updating the JS render functions.

## Coding Conventions

- Python 3.11+, full type annotations
- Pydantic v2 for API models; dataclasses for domain objects
- Async throughout — uses aiosqlite for non-blocking DB access
- No hardcoded credentials, no hardcoded instrument lists — all config via env
- Dry-run stubs return structurally valid responses so the app can run without OANDA
- All tests use `pytest-asyncio` in `auto` mode (no `@pytest.mark.asyncio` needed)
- No comments on obvious code; comments only for non-obvious invariants

## Running Locally

```bash
cp .env.example .env
uvicorn app.main:app --reload      # API + dashboard on :8000
python scripts/run_worker.py       # standalone worker (optional)
pytest -v                          # full test suite
```

## Railway Deployment

See `Dockerfile` and `railway.toml`. Set env vars in Railway dashboard, mount a volume at `/data`, and point `DATABASE_URL=sqlite+aiosqlite:////data/trader.db`.

## Safety Rules

1. Never set `TRADING_ENABLED=true` without verifying all risk limits
2. The kill switch stops the worker after 5 consecutive tick errors — check logs
3. `POST /control/flatten` is the emergency stop — closes all open trades via the broker
4. `DRY_RUN=true` is the default — orders are logged but never sent to OANDA
5. Daily limits (MAX_TRADES_PER_DAY, MAX_LOSSES_PER_DAY) reset at UTC midnight automatically
