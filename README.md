# oanda-apex-bot

A production-style autonomous forex trading bot targeting the OANDA v20 REST API with a live dashboard, MA-crossover strategy, and Apex-challenge simulator seam.

Safe by default — `DRY_RUN=true`, `TRADING_ENABLED=false`.

## Features

- **FastAPI control plane** — pause, resume, flatten, toggle trading, inspect state
- **Live dashboard** at `/dashboard` — auto-refreshing, dark-themed, control buttons
- **Async OANDA v20 client** — httpx-powered, retry/backoff, dry-run aware
- **MA-crossover + breakout strategy** — short/long SMA + N-bar breakout levels
- **SQLite persistence** — SQLAlchemy 2.0 async, trades + journal log
- **Autonomous worker loop** — market-hours gated, pause/resume via API
- **Daily limits** — max trades per day, max losses per day with midnight auto-reset
- **Risk controls** — single open trade, position size limits, daily loss cap, kill switch
- **Apex simulator** — `ApexSimulatorPolicy` enforces funded-challenge rules (daily loss, trailing drawdown, profit target)
- **Railway-ready** — Dockerfile + railway.toml included

## Quickstart

```bash
git clone <repo> && cd trader
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload   # API + dashboard on :8000
```

Open [http://localhost:8000/dashboard](http://localhost:8000/dashboard) for the live dashboard.

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/state` | Worker state, daily stats, Apex status |
| GET | `/trades` | Recent trade history |
| GET | `/dashboard` | Live HTML dashboard |
| POST | `/control/pause` | Pause the worker loop |
| POST | `/control/resume` | Resume the worker loop |
| POST | `/control/toggle-trading` | Toggle TRADING_ENABLED at runtime |
| POST | `/control/flatten` | Close all open trades immediately |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OANDA_API_KEY` | `""` | Practice account API key |
| `OANDA_ACCOUNT_ID` | `""` | Practice account ID |
| `OANDA_BASE_URL` | `https://api-fxpractice.oanda.com` | OANDA base URL |
| `DRY_RUN` | `true` | Stub all broker calls |
| `TRADING_ENABLED` | `false` | Actually place orders |
| `INSTRUMENTS` | `EUR_USD,GBP_USD,USD_JPY` | Comma-separated instrument list |
| `WORKER_INTERVAL_SECONDS` | `15` | Tick interval |
| `STOP_LOSS_PIPS` | `20` | Stop-loss distance in pips |
| `TAKE_PROFIT_PIPS` | `40` | Take-profit distance in pips |
| `MAX_OPEN_TRADES` | `1` | Maximum concurrent open trades |
| `MAX_TRADES_PER_DAY` | `3` | Daily trade limit |
| `MAX_LOSSES_PER_DAY` | `2` | Daily loss count limit |
| `SHORT_MA_PERIOD` | `10` | Short MA candle count |
| `LONG_MA_PERIOD` | `30` | Long MA candle count |
| `BREAKOUT_LOOKBACK` | `20` | Breakout channel lookback |
| `CANDLE_COUNT` | `60` | Candles to fetch per cycle |
| `TRADE_UNITS` | `100` | Units per order |
| `APEX_ENABLED` | `false` | Enable Apex challenge rules |
| `APEX_ACCOUNT_SIZE` | `100000` | Simulated account size |
| `APEX_MAX_DAILY_LOSS_PCT` | `0.02` | Daily loss limit (2%) |
| `APEX_TRAILING_DRAWDOWN_PCT` | `0.04` | Trailing drawdown limit (4%) |
| `APEX_PROFIT_TARGET_PCT` | `0.08` | Profit target (8%) |

## Railway Deployment

1. Push this repo to GitHub.
2. Create a new Railway project, link the repo.
3. Add environment variables in the Railway dashboard (copy from `.env.example`).
4. Set `DATABASE_URL=sqlite+aiosqlite:////data/trader.db` and attach a Railway volume at `/data`.
5. Set credentials and `DRY_RUN=false`, `TRADING_ENABLED=true` when ready to go live.

The `railway.toml` configures the Dockerfile build and health-check at `/health`.

## Running Tests

```bash
pytest -v
```

## Strategy

The signal engine evaluates per instrument on each tick:

1. Fetch M5 candles (default: 60 bars)
2. Compute short SMA (10-bar) and long SMA (30-bar)
3. Compute breakout high/low over last 20 bars
4. **BUY** if `short_ma > long_ma AND price > breakout_high`
5. **SELL** if `short_ma < long_ma AND price < breakout_low`
6. **HOLD** otherwise

Orders attach stop-loss and take-profit calculated in pips from the current mid-price.

## Safety Model

- No order is placed unless `TRADING_ENABLED=true`
- `DRY_RUN=true` stubs all broker calls — boots with empty credentials
- Daily limits block trading after N trades or N losses
- Single-open-trade limit prevents pyramiding
- Kill switch stops the worker after consecutive errors
- `POST /control/flatten` closes all trades immediately
