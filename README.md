# oanda-apex-bot

A production-style async Python forex trading bot targeting the OANDA v20 REST API.
Ships with safe defaults — no real money moves without explicit opt-in.

## Features

- **FastAPI control plane** — pause, resume, inspect state, query trades
- **Async OANDA v20 client** — `httpx`-powered, dry-run aware
- **SQLite persistence** — `SQLAlchemy 2.0` async, trades + journal log
- **Autonomous worker loop** — market-hours gated, pause/resume via API
- **Risk controls** — position size limits, daily loss cap, kill switch
- **Apex simulator seam** — `ExecutionPolicy` protocol ready for funded-challenge injection
- **Safe by default** — `DRY_RUN=true`, `TRADING_ENABLED=false`

## Quickstart

```bash
# 1. Clone and set up environment
git clone <repo>
cd trader
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env — credentials optional when DRY_RUN=true

# 3. Run the API
uvicorn app.main:app --reload
# → http://localhost:8000

# 4. Run the worker (separate terminal)
python scripts/run_worker.py

# 5. Run tests
pytest -v
```

## API Endpoints

| Method | Path              | Description                   |
|--------|-------------------|-------------------------------|
| GET    | `/health`         | Liveness check                |
| GET    | `/state`          | Worker status + settings      |
| GET    | `/trades`         | All persisted trades          |
| POST   | `/control/pause`  | Pause the worker loop         |
| POST   | `/control/resume` | Resume the worker loop        |

### Quick curl examples

```bash
curl http://localhost:8000/health
curl http://localhost:8000/state
curl http://localhost:8000/trades
curl -X POST http://localhost:8000/control/pause
curl -X POST http://localhost:8000/control/resume
```

## Environment Variables

| Variable                  | Default                                  | Description                          |
|---------------------------|------------------------------------------|--------------------------------------|
| `OANDA_API_KEY`           | *(empty)*                                | OANDA practice API key               |
| `OANDA_ACCOUNT_ID`        | *(empty)*                                | OANDA practice account ID            |
| `OANDA_BASE_URL`          | `https://api-fxpractice.oanda.com`       | OANDA v20 API base URL               |
| `TRADING_ENABLED`         | `false`                                  | Must be `true` to send real orders   |
| `DRY_RUN`                 | `true`                                   | Stubs all broker calls               |
| `LOG_LEVEL`               | `INFO`                                   | Python log level                     |
| `TIMEZONE`                | `America/New_York`                       | Market-hours timezone                |
| `DATABASE_URL`            | `sqlite+aiosqlite:///./trader.db`        | SQLAlchemy async DB URL              |
| `WORKER_INTERVAL_SECONDS` | `30`                                     | Seconds between each worker tick     |
| `INSTRUMENTS`             | `EUR_USD,GBP_USD`                        | Comma-separated instrument list      |
| `MAX_POSITION_UNITS`      | `1000`                                   | Max units per order                  |
| `DAILY_LOSS_LIMIT_USD`    | `50.0`                                   | Stop trading after this daily loss   |

## Project Layout

```
app/
  main.py          FastAPI app factory + lifespan (all wiring here)
  config.py        pydantic-settings Settings
  api/             Route handlers (no business logic)
  core/            Pure utilities: clock, enums, ids, logging
  broker/          OANDA v20 async HTTP client
  data/            Response parsers and normalisers
  strategy/        Signal engine + ExecutionPolicy (Apex seam)
  risk/            RiskLimits + KillSwitch
  services/        Orchestration: worker loop, Trader, journaling, reconciler
  storage/         SQLAlchemy models + async repositories
  schemas/         Pydantic API models + domain dataclasses
tests/             pytest suite
scripts/           CLI entrypoints (run_api.py, run_worker.py)
```

## Safety Model

Two independent guards prevent accidental live trading:

1. **`DRY_RUN=true`** — stubs every broker call; nothing reaches OANDA
2. **`TRADING_ENABLED=false`** — `Trader.execute()` skips order placement

Both must be disabled for real orders:

```env
DRY_RUN=false
TRADING_ENABLED=true
OANDA_API_KEY=your-practice-key
OANDA_ACCOUNT_ID=your-account-id
```

## Apex Simulator

The `ExecutionPolicy` in `app/strategy/execution_policy.py` accepts an optional
`simulator: ApexSimulator` argument. Implement the `ApexSimulator` protocol and
inject it at startup (in `app/main.py`) to route all orders through funded-challenge
rules instead of OANDA — zero changes to any other module.

See `AGENTS.md` for the full extension guide.

## Docker

No Dockerfile yet. To containerise:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## What's Implemented vs TODO

### Implemented
- FastAPI app with 5 endpoints
- OANDA client with 6 methods (all dry-run safe)
- SQLite schema: `trades` + `journal_entries`
- Async worker loop with market-hours gating and pause/resume
- Risk limits + kill switch
- Signal engine scaffold (returns `None` / hold)
- Execution policy with Apex simulator seam
- Journaling + reconciler (reconciler is a stub)
- Full test suite (health API, clock, config)

### TODO
- Real signal logic (EMA crossover, RSI, etc.)
- `ApexSimulatorPolicy` for Apex-challenge rules
- Dockerfile + docker-compose
- OANDA streaming price feed
- Prometheus `/metrics` endpoint
- Alembic migration scripts
- Railway / cloud deployment config
