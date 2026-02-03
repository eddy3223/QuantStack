# QuantPlatform

A systematic trading data pipeline and backtesting platform. It covers ETL from market data sources, feature engineering, signal generation, and vectorized multi-asset backtesting.

---

## Quick start

From the project root (repository root, not `quant_trading_system`):

```bash
cd quant_trading_system
poetry install
mkdir -p data
poetry run python scripts/cli.py data load AAPL MSFT --days 365
poetry run streamlit run app.py
```

Then in the browser: open **Backtest**, click **Run Backtest**, then open **Analytics** to see metrics and charts. Total time: under 2 minutes.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  DATA LAYER                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐ │
│  │ YFinance     │     │ ETL Pipeline │     │ SQLite / PostgreSQL      │ │
│  │ (sources/)   │ ──► │ (etl/)       │ ──► │ (models, database)      │ │
│  └──────────────┘     └──────────────┘     └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ANALYTICS LAYER                                                         │
│  ┌──────────────┐     ┌──────────────┐                                   │
│  │ FeatureEngine│     │ Signals      │  (momentum, RSI, MACD, combiner)  │
│  │ (features.py)│ ──► │ (signals.py) │                                   │
│  └──────────────┘     └──────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  TRADING LAYER                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ BacktestEngine  (multi-asset, vectorized, no lookahead)           │  │
│  │ → BacktestResult (returns, Sharpe, drawdown, per-asset metrics)   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

- **Data:** Normalized DB (instruments, daily prices, ETL job log). ETL is idempotent and logs per-symbol status.
- **Analytics:** Returns, volatility, moving averages, RSI, MACD, Bollinger, ATR; signals in {-1, 0, +1}.
- **Trading:** Backtest uses previous-day signals, supports transaction costs and optional vol targeting. Risk/diagnostics (drawdown duration, turnover, report) live in `DiagnosticEngine`.

### Design notes

- **DataSource abstraction** — All market data goes through a common interface (YFinance, FRED, Stub). That keeps ETL and DB schema vendor-agnostic and makes it easy to add sources or test with synthetic data.
- **Vectorized backtest** — The engine runs on full price/signal DataFrames with no lookahead (signals are shifted so position at t uses signal from t−1). This keeps the implementation simple and fast.
- **Idempotent ETL** — Loads skip existing (symbol, date) pairs and log per-symbol success/failure. Re-running the same load is safe and makes debugging and incremental updates straightforward.
- **SQLite by default** — Chosen for zero-config and portability. For production you’d typically use PostgreSQL (or similar) with connection pooling; the code path is the same, only `DATABASE_URL` changes.

---

## Prerequisites

- **Python** 3.10+
- **Poetry** ([install](https://python-poetry.org/docs/#installation))

---

## Install

```bash
cd quant_trading_system
poetry install
```

Optional: `poetry install --with trading` for Alpaca-related dependencies.

---

## Runbook

### 1. Load market data

Load daily history for one or more symbols. Data is stored in `data/quant_data.db` (SQLite by default).

```bash
# Last 30 days for AAPL, MSFT
poetry run python scripts/cli.py data load AAPL MSFT

# One year for more symbols
poetry run python scripts/cli.py data load AAPL MSFT GOOGL --days 365

# Custom date range
poetry run python scripts/cli.py data load SPY --start-date 2023-01-01 --end-date 2024-12-31
```

**First run:** Ensure the `data/` directory exists (e.g. `mkdir data`); the ETL will create the DB file if missing.

---

### 2. Inspect loaded data

```bash
# List instruments and optional price counts
poetry run python scripts/cli.py data list
poetry run python scripts/cli.py data list --prices

# Recent ETL job status
poetry run python scripts/cli.py data status --limit 5

# Last 10 days of prices for a symbol
poetry run python scripts/cli.py data query AAPL --days 10
```

---

### 3. Run a backtest (script)

The backtest test script loads prices from the DB, builds features and signals (momentum + RSI + MACD combiner) per asset, runs the backtest, and plots.

**Prerequisite:** Load at least the symbols used in the test (e.g. AAPL, MSFT). Edit `tests/test_backtest.py` to set `SYMBOLS` to the list you want.

```bash
# Load data first
poetry run python scripts/cli.py data load AAPL MSFT --days 365

# Run backtest and open plots
poetry run python tests/test_backtest.py
```

You should see printed metrics (total return, Sharpe, max drawdown, win rate) and matplotlib figures (portfolio + per-asset equity, drawdown, per-asset curves).

---

### 3a. Run the Streamlit app (UI)

A Streamlit UI lets you load data, run backtests, and view results in the browser.

**Start the app** (from the `quant_trading_system` directory):

```bash
cd quant_trading_system
poetry run streamlit run app.py
```

A browser tab will open. Use the sidebar to switch pages:

- **Data** — List instruments in the database; load new data (symbols, days); select a symbol and view a price chart. Load stats are shown after a run and the list refreshes.
- **Backtest** — Select symbols, date range, and engine parameters (capital, volatility target, costs, etc.). Click **Run Backtest** to run the backtest; metrics (total return, Sharpe, max drawdown, win rate) appear below. The result is stored for the Analytics page.
- **Analytics** — View the **last** backtest result: the same metrics, plus portfolio equity curve, drawdown chart, and per-asset equity. Expand **Risk & diagnostics report** for drawdown duration, turnover, and a full diagnostics dict. If no backtest has been run yet, run one from the Backtest page first.

**From repo root:** `poetry run streamlit run quant_trading_system/app.py` (run from the directory that contains `quant_trading_system`).

---

### 4. Run tests (unit/integration)

```bash
# All tests
poetry run pytest tests/ -v

# Single test file
poetry run pytest tests/test_backtest.py -v
poetry run pytest tests/test_pipeline.py -v
poetry run pytest tests/test_features.py -v
poetry run pytest tests/test_db.py -v
poetry run pytest tests/test_source.py -v
```

**Note:** `test_backtest.py` is a script that loads from DB and plots; run it directly as in step 3. Other tests in `tests/` are pytest-based.

---

### 5. Use a different database (e.g. PostgreSQL)

Set the connection URL (and ensure the DB and schema exist). The app uses the same code path; only the URL changes.

```bash
# Windows (PowerShell)
$env:DATABASE_URL = "postgresql://user:password@localhost:5432/quantdb"

# Linux / macOS
export DATABASE_URL="postgresql://user:password@localhost:5432/quantdb"
```

Then run any data or backtest commands as above. If you use SQLite, omit `DATABASE_URL` to keep the default `data/quant_data.db`.

---

## Project structure

```
quant_trading_system/
├── README.md           # This file
├── app.py              # Streamlit UI (Data, Backtest, Analytics pages)
├── pyproject.toml      # Dependencies and project config
├── data/               # SQLite DB file (created by ETL)
├── scripts/
│   └── cli.py          # CLI: data load, list, status, query
├── src/
│   ├── data/           # Data layer
│   │   ├── models.py       # DB models (Instrument, PriceDaily, DataLoadLog, …)
│   │   ├── database.py     # Engine, session, init_database
u[]
2. **Request an API key** at [FRED API keys](https://fredaccount.stlouisfed.org/apikeys) (while logged in).
3. **Set the key** in your environment or in a `.env` file:
   - **Environment:** `set FRED_API_KEY=your_key_here` (Windows) or `export FRED_API_KEY=your_key_here` (Linux/macOS).
   - **`.env`:** Copy `.env.example` to `.env` and add `FRED_API_KEY=your_key_here`. Load it with `python-dotenv` if your app supports it.

YFinance and the Stub source work without any API key. Optional trading/execution features may use `.env` for other keys (e.g. Alpaca).

---

## Production considerations

For a production deployment you would typically add:

- **Schema migrations** — e.g. Alembic (or similar) so DB changes are versioned and repeatable.
- **ETL robustness** — Retries with backoff and rate limiting for external APIs (YFinance, FRED); optional dead-letter handling for failed symbols.
- **Secrets** — No API keys in repo; use env vars or a secret manager; rotate keys if they were ever committed.
- **Streamlit** — If the UI is exposed, add auth and consider running behind a reverse proxy; for internal use, headless run is often enough.

---

## License

See [LICENSE](LICENSE) in the repository root.
