# QuantPlatform

A systematic trading data pipeline and backtesting platform. It covers ETL from market data sources, feature engineering, signal generation, and vectorized multi-asset backtesting.

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
- **Trading:** Backtest uses previous-day signals, supports transaction costs and optional vol targeting.

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
├── pyproject.toml      # Dependencies and project config
├── data/               # SQLite DB file (created by ETL)
├── scripts/
│   └── cli.py          # CLI: data load, list, status, query
├── src/
│   ├── data/           # Data layer
│   │   ├── models.py       # DB models (Instrument, PriceDaily, DataLoadLog, …)
│   │   ├── database.py     # Engine, session, init_database
│   │   ├── sources/        # Data source adapters (YFinance, base)
│   │   └── etl/
│   │       └── pipeline.py # ETL pipeline
│   ├── analytics/
│   │   ├── features.py    # FeatureEngine (returns, vol, MA, RSI, MACD, …)
│   │   └── signals.py     # Momentum, RSI, MACD, SignalCombiner
│   └── trading/
│       └── backtest.py    # BacktestEngine, BacktestResult, plotting
└── tests/
    ├── test_db.py
    ├── test_source.py
    ├── test_pipeline.py
    ├── test_features.py
    └── test_backtest.py   # Multi-asset backtest + plots
```

---

## Configuration

| Item | Default | Override |
|------|--------|----------|
| Database | `sqlite:///./data/quant_data.db` | Set `DATABASE_URL` |
| ETL cache / paths | In project `data/` | N/A |

No API keys are required for the data layer (YFinance is used without auth). Optional trading/execution features may use `.env` for keys (e.g. Alpaca).

---

## License

See [LICENSE](LICENSE) in the repository root.
