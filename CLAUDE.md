# CLAUDE.md

## Project Overview

Two components:

1. **GLD Trend-Following Strategy** — Quantitative trading system for the GLD ETF with multi-component trend-following, backtesting, and automated parameter optimization.
2. **Scalp Dashboard** — Real-time web dashboard that monitors US stock tick data from Polygon.io, surfacing stocks with high trade frequency and wide price gaps for scalping opportunities.

**Language:** Python 3
**Dependencies (strategy):** pandas, numpy, scipy, matplotlib — install with `pip install pandas numpy scipy matplotlib`
**Dependencies (dashboard):** fastapi, uvicorn, websockets, numpy — install with `pip install -r dashboard/requirements.txt`

## Repository Structure

```
strategy.py              # Core strategy: technical indicators + TrendFollowingStrategy class
run_strategy.py          # Main entry point: data → optimize → backtest → report + charts
optimize.py              # Parameter optimization: grid search, differential evolution, walk-forward
fetch_data.py            # Data fetching from Yahoo Finance with synthetic fallback
scalp_symbols.csv        # Ticker list for the scalp dashboard (one ticker per row)

dashboard/
  server.py              # FastAPI backend: Polygon WebSocket, trade buffering, metric computation
  index.html             # Single-page frontend: dark-themed sortable/filterable table
  requirements.txt       # Python dependencies for the dashboard
```

Generated artifacts (checked in):
- `gld_data.csv` — Raw GLD price data
- `backtest_results.csv` — Full daily backtest output
- `optimisation_results.csv` — Grid search results
- `gld_strategy_report.png` — 7-panel performance dashboard

## Running the Project

```bash
python3 run_strategy.py
```

This runs the full pipeline: load data → grid search → differential evolution → final backtest → walk-forward validation → generate report and charts.

Individual modules (`strategy.py`, `optimize.py`, `fetch_data.py`) are library modules imported by `run_strategy.py` and are not intended to be run directly.

### Scalp Dashboard

```bash
# Install dependencies
pip install -r dashboard/requirements.txt

# Live mode (requires Polygon.io API key)
export POLYGON_API_KEY=your_key_here
python dashboard/server.py

# Demo mode (synthetic trade data, no API key needed)
python dashboard/server.py --demo

# Custom port
python dashboard/server.py --demo --port 9000
```

Open `http://localhost:8000` in a browser. The dashboard streams real-time trade data and computes per-ticker metrics (trade frequency, price-gap standard deviation, trend, spread/trend ratio). All columns are sortable (click headers) and filterable (type `>100`, `<50`, `10..500`, etc. in filter inputs).

## Architecture

**Linear pipeline:** Data → Optimize → Backtest → Visualize → Report

### Module Responsibilities

- **fetch_data.py** — `load_gld_data()` fetches GLD OHLCV data from Yahoo Finance (CSV endpoint with v8 JSON API fallback). Falls back to `generate_synthetic_gld()` if network is unavailable. Includes retry logic with exponential backoff.

- **strategy.py** — Contains standalone technical indicator functions (`ema`, `sma`, `atr`, `donchian_upper`, `donchian_lower`, `roc`) and the `TrendFollowingStrategy` class. The strategy computes a weighted composite signal from 5 components: dual EMA crossover (25%), Donchian breakout (25%), ROC momentum (20%), trend filter (15%), MACD histogram (15%). A 6th component (volatility regime filter) scales exposure. The `backtest()` method applies the strategy to a DataFrame and returns daily results with cumulative performance.

- **optimize.py** — Three optimization approaches: `grid_search()` for broad parameter exploration, `scipy_optimize()` using differential evolution for continuous refinement, and `walk_forward_validation()` with 5-fold expanding windows for out-of-sample testing. Objective function maximizes Sharpe ratio with a drawdown penalty (>30%) and CAGR tiebreaker.

- **run_strategy.py** — Orchestrates the pipeline. `plot_results()` generates a 7-panel matplotlib dashboard. `print_report()` formats console output. `main()` ties everything together. Uses `matplotlib.use("Agg")` for headless rendering.

### Scalp Dashboard Architecture

**Backend (`dashboard/server.py`):**
- FastAPI serves the HTML frontend and a WebSocket endpoint (`/ws`)
- Connects to Polygon.io WebSocket (`wss://socket.polygon.io/stocks`) for real-time trade ticks
- Stores trades per ticker in rolling deques (up to 60 min, 500K trades max per ticker)
- Every 1 second, computes metrics for all tickers and broadcasts JSON to connected frontends
- Accepts parameter updates and pause/resume commands from the frontend over the same WebSocket
- `--demo` mode generates synthetic random-walk trades for testing without an API key

**Frontend (`dashboard/index.html`):**
- Single-file SPA (inline CSS + JS, no build step)
- Dark terminal-style theme
- Dynamic parameter inputs: Min Shares, Trade Count Window (sec), StdDev Window (min), Trend Window (min)
- Sortable columns (click header to cycle: none → asc → desc)
- Per-column filter expressions: `>N`, `<N`, `>=N`, `<=N`, `N..M` (between), text substring for ticker
- Pause/Resume button stops/resumes the Polygon data feed server-side
- Auto-reconnects WebSocket on disconnect

**Dashboard columns:**
| Column | Description |
|--------|-------------|
| Ticker | Symbol |
| Last Price | Most recent trade price (any size) |
| Trades / Win | Count of trades >= min_shares in the count window |
| $ Gap StdDev | Std dev of consecutive price gaps (size-filtered, over std window) |
| % Gap StdDev | Same in percentage terms |
| Trend ($/min) | Linear regression slope of prices over the trend window |
| StdDev / Trend | Ratio of $ gap std dev to \|trend\|; high = wide spreads + no trend = scalp opportunity |

### Strategy Parameters (16 total)

Key parameters with defaults: `fast_ema=10`, `slow_ema=50`, `trend_ema=200`, `macd_fast=12`, `macd_slow=26`, `macd_signal=9`, `donchian_window=55`, `roc_period=60`, `atr_window=20`, `signal_smooth=3`, `long_threshold=0.15`, `short_threshold=-0.15`, `vol_target=0.16`, `dd_limit=0.15`, `min_holding=3`, `transaction_cost_bps=5.0`.

Constraint: `fast_ema < slow_ema < trend_ema` (enforced in grid search).

### Risk Management

- Volatility targeting: scales position size to a daily vol target derived from `vol_target`
- Drawdown control: reduces exposure when drawdown exceeds `dd_limit`
- Signal smoothing: `signal_smooth`-period window reduces whipsaws
- Minimum holding period: `min_holding` days prevents excessive turnover
- Transaction cost modeling: `transaction_cost_bps` applied per trade

## Code Conventions

- **Vectorized pandas/numpy operations** — avoids Python loops for performance
- **Type hints** on function signatures (e.g., `series: pd.Series`, `span: int`)
- **Docstrings** at module and class level; functions have brief inline comments
- **Configuration via parameter dicts** — strategy behavior controlled by passing keyword arguments to `TrendFollowingStrategy`
- **`performance_metrics()` is a static method** — can be called without instantiating the class
- **Print-based progress reporting** — no structured logging framework
- **NaN handling** — uses `.fillna()` and `.dropna()` throughout signal computation
- **Naming** — snake_case for functions/variables, PascalCase for classes, British spelling in comments/filenames (e.g., "optimisation")

## Testing

There is no formal test suite (no pytest, unittest, or test directory). Validation is performed through walk-forward out-of-sample testing in `optimize.py:walk_forward_validation()`.

## CI/CD

None configured. No GitHub Actions, pre-commit hooks, or linting setup.

## Git Conventions

- Commit messages are descriptive single-line summaries
- `.gitignore` only excludes `__pycache__/`
- Generated data files (CSV, PNG) are tracked in git
