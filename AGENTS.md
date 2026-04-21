# AGENTS.md — oanda-apex-bot

Conventions and extension points for AI agents and human contributors.

## Project Overview

Automated forex practice-trading bot targeting OANDA's v20 REST API.
Safe by default: `DRY_RUN=true`, `TRADING_ENABLED=false` — no real money moves without explicit opt-in.

## Coding Conventions

- Python 3.11+, type hints everywhere, no `Any` unless unavoidable
- Pydantic v2 for all data models (schemas/ and domain objects)
- `async def` for I/O-bound operations; sync SQLAlchemy for DB (wrapped in executor if needed)
- No ML, no external signal services — keep logic deterministic and auditable
- Each module has a single responsibility; prefer composition over inheritance

## Key Extension Points

### Apex Simulator Seam

The `ExecutionPolicy` protocol in `app/strategy/execution_policy.py` is the primary hook
for injecting an Apex-style funded-challenge simulator.

```python
# app/strategy/execution_policy.py
class ExecutionPolicy(Protocol):
    def should_execute(self, signal: Signal) -> bool: ...
    def on_fill(self, result: dict) -> None: ...
```

To add Apex simulation:
1. Create `app/strategy/apex_simulator.py`
2. Implement `ApexSimulatorPolicy(ExecutionPolicy)` tracking:
   - daily loss limit (e.g. -2% of account)
   - max trailing drawdown (e.g. -5%)
   - profit target (e.g. +8%)
   - minimum trading days
3. Inject via `app/main.py` lifespan instead of `LiveExecutionPolicy`

No other files need to change.

### Adding New Instruments

`Trader.tick()` in `app/services/trader.py` passes a hardcoded instrument list to
`get_latest_prices`. Extend this list or make it configurable via `Settings`.

### Adding New Signals

`SignalEngine.evaluate()` in `app/strategy/signal_engine.py` returns `Signal | None`.
Add new strategies by computing features in `app/strategy/features.py` and composing
them in `signal_engine.py`.

### Adding New Risk Rules

Extend `RiskLimits` in `app/risk/limits.py`. The `check_order()` method returns
`(bool, reason_str)` — add new checks there without breaking callers.

## Directory Map

```
app/
  main.py              FastAPI app factory + lifespan (dependency wiring)
  config.py            Settings (pydantic-settings, env-driven)
  api/                 HTTP route handlers only — no business logic
  core/                Pure utilities: clock, enums, ids, logging
  broker/              OANDA v20 HTTP client (dry-run aware)
  data/                Response parsers and normalisers
  strategy/            Signal generation + ExecutionPolicy (Apex seam)
  risk/                RiskLimits + KillSwitch
  services/            Orchestration: worker loop, Trader, journaling, reconciler
  storage/             SQLAlchemy models + repositories
  schemas/             Pydantic models: domain objects + API contracts
tests/                 pytest suite
scripts/               Runnable entrypoints
```

## Running Locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # edit if you have OANDA practice credentials
uvicorn app.main:app --reload # API on http://localhost:8000
python scripts/run_worker.py  # worker loop (separate terminal)
pytest -v                     # run test suite
```

## Environment Variables

| Variable            | Default                              | Description                         |
|---------------------|--------------------------------------|-------------------------------------|
| `OANDA_API_KEY`     | (empty)                              | OANDA practice API key              |
| `OANDA_ACCOUNT_ID`  | (empty)                              | OANDA practice account ID           |
| `OANDA_BASE_URL`    | https://api-fxpractice.oanda.com     | OANDA API base URL                  |
| `TRADING_ENABLED`   | false                                | Set true to send real orders        |
| `DRY_RUN`           | true                                 | Stub all broker calls               |
| `LOG_LEVEL`         | INFO                                 | Python logging level                |
| `TIMEZONE`          | America/New_York                     | Timezone for market-hours checks    |

## Safety Rules

- Never set `TRADING_ENABLED=true` without valid OANDA practice credentials
- The kill switch (`/control/pause` or `KillSwitch.trigger()`) stops order placement immediately
- `DRY_RUN=true` stubs ALL broker calls — nothing reaches OANDA servers
- `TRADING_ENABLED=false` is a second guard: even with live credentials, orders won't be placed

## TODO / Planned Work

- [ ] Apex simulator policy (`strategy/apex_simulator.py`)
- [ ] Real signal logic (EMA crossover, RSI filters)
- [ ] Dockerfile + docker-compose
- [ ] OANDA streaming price feed
- [ ] Prometheus `/metrics` endpoint
- [ ] Alembic migration scripts
- [ ] Railway deployment config
