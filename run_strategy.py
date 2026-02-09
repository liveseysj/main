#!/usr/bin/env python3
"""
Main runner: Load data → Optimise → Backtest → Report + Charts.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from fetch_data import load_gld_data
from strategy import TrendFollowingStrategy
from optimize import grid_search, scipy_optimize, walk_forward_validation


def plot_results(df: pd.DataFrame, params: dict, metrics: dict, oos_df: pd.DataFrame | None = None):
    """Generate comprehensive performance charts."""

    fig = plt.figure(figsize=(18, 22))
    gs = fig.add_gridspec(5, 2, hspace=0.35, wspace=0.25)

    # ---- 1. Cumulative returns ----
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(df["Date"], df["cum_asset"], label="Buy & Hold GLD", alpha=0.8, linewidth=1.2)
    ax1.plot(df["Date"], df["cum_strategy"], label="Trend Strategy (net)", linewidth=1.5, color="darkgreen")
    ax1.set_title("Cumulative Returns: Trend Strategy vs Buy & Hold", fontsize=13, fontweight="bold")
    ax1.set_ylabel("Growth of $1")
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale("log")

    # ---- 2. Drawdown ----
    ax2 = fig.add_subplot(gs[1, :])
    cum = (1 + df["strategy_return_net"]).cumprod()
    dd = (cum - cum.cummax()) / cum.cummax() * 100
    ax2.fill_between(df["Date"], dd, 0, color="red", alpha=0.3)
    ax2.plot(df["Date"], dd, color="darkred", linewidth=0.8)
    ax2.set_title("Strategy Drawdown", fontsize=13, fontweight="bold")
    ax2.set_ylabel("Drawdown (%)")
    ax2.grid(True, alpha=0.3)

    # ---- 3. Position over time ----
    ax3 = fig.add_subplot(gs[2, :])
    ax3.fill_between(df["Date"], df["position"], 0,
                     where=df["position"] > 0, color="green", alpha=0.3, label="Long")
    ax3.fill_between(df["Date"], df["position"], 0,
                     where=df["position"] < 0, color="red", alpha=0.3, label="Short")
    ax3.set_title("Position Over Time (+1=Long, -1=Short, 0=Flat)", fontsize=13, fontweight="bold")
    ax3.set_ylabel("Position")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # ---- 4. Rolling Sharpe (1-year) ----
    ax4 = fig.add_subplot(gs[3, 0])
    rolling_sharpe = (
        df["strategy_return_net"].rolling(252).mean()
        / df["strategy_return_net"].rolling(252).std()
        * np.sqrt(252)
    )
    ax4.plot(df["Date"], rolling_sharpe, color="navy", linewidth=1)
    ax4.axhline(y=0, color="red", linestyle="--", alpha=0.5)
    ax4.axhline(y=metrics["sharpe_ratio"], color="green", linestyle="--", alpha=0.5, label=f'Full-period Sharpe={metrics["sharpe_ratio"]:.2f}')
    ax4.set_title("Rolling 1-Year Sharpe Ratio", fontsize=12, fontweight="bold")
    ax4.set_ylabel("Sharpe")
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    # ---- 5. Monthly returns heatmap ----
    ax5 = fig.add_subplot(gs[3, 1])
    monthly = df.set_index("Date")["strategy_return_net"].resample("ME").apply(lambda x: (1 + x).prod() - 1) * 100
    monthly_df = pd.DataFrame({
        "Year": monthly.index.year,
        "Month": monthly.index.month,
        "Return": monthly.values,
    })
    pivot = monthly_df.pivot_table(index="Year", columns="Month", values="Return", aggfunc="mean")
    # Only show last 10 years for readability
    if len(pivot) > 10:
        pivot = pivot.iloc[-10:]
    im = ax5.imshow(pivot.values, cmap="RdYlGn", aspect="auto", vmin=-8, vmax=8)
    ax5.set_xticks(range(12))
    ax5.set_xticklabels(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], fontsize=7)
    ax5.set_yticks(range(len(pivot)))
    ax5.set_yticklabels(pivot.index, fontsize=7)
    ax5.set_title("Monthly Returns Heatmap (%)", fontsize=12, fontweight="bold")
    plt.colorbar(im, ax=ax5, shrink=0.8)

    # ---- 6. Signal components ----
    ax6 = fig.add_subplot(gs[4, 0])
    ax6.plot(df["Date"].iloc[-504:], df["smooth_signal"].iloc[-504:], label="Composite Signal", linewidth=1.2, color="purple")
    lt = params.get("long_threshold", 0.15)
    st = params.get("short_threshold", -0.15)
    ax6.axhline(y=lt, color="green", linestyle="--", alpha=0.4, label=f"Long threshold ({lt})")
    ax6.axhline(y=st, color="red", linestyle="--", alpha=0.4, label=f"Short threshold ({st})")
    ax6.axhline(y=0, color="gray", linestyle="-", alpha=0.3)
    ax6.set_title("Composite Signal (Last 2 Years)", fontsize=12, fontweight="bold")
    ax6.legend(fontsize=7)
    ax6.grid(True, alpha=0.3)

    # ---- 7. Annual returns comparison ----
    ax7 = fig.add_subplot(gs[4, 1])
    annual_strat = df.set_index("Date")["strategy_return_net"].resample("YE").apply(lambda x: (1 + x).prod() - 1) * 100
    annual_asset = df.set_index("Date")["asset_return"].resample("YE").apply(lambda x: (1 + x).prod() - 1) * 100
    years = annual_strat.index.year
    x = np.arange(len(years))
    width = 0.35
    ax7.bar(x - width/2, annual_asset.values, width, label="Buy & Hold", alpha=0.7, color="steelblue")
    ax7.bar(x + width/2, annual_strat.values, width, label="Strategy", alpha=0.7, color="darkgreen")
    ax7.set_xticks(x)
    ax7.set_xticklabels(years, rotation=45, fontsize=7)
    ax7.set_title("Annual Returns Comparison (%)", fontsize=12, fontweight="bold")
    ax7.set_ylabel("Return (%)")
    ax7.legend(fontsize=8)
    ax7.grid(True, alpha=0.3, axis="y")

    plt.savefig("gld_strategy_report.png", dpi=150, bbox_inches="tight")
    print("\nChart saved to gld_strategy_report.png")
    plt.close()


def print_report(metrics_strat: dict, metrics_bh: dict, best_params: dict, grid_df: pd.DataFrame):
    """Print a formatted performance report."""

    print("\n" + "=" * 72)
    print("       GLD TREND-FOLLOWING STRATEGY — PERFORMANCE REPORT")
    print("=" * 72)

    print(f"\n{'Metric':<30} {'Strategy':>15} {'Buy & Hold':>15}")
    print("-" * 62)
    rows = [
        ("Total Return (%)", "total_return_pct", ".1f"),
        ("CAGR (%)", "cagr_pct", ".1f"),
        ("Ann. Volatility (%)", "ann_volatility_pct", ".1f"),
        ("Sharpe Ratio", "sharpe_ratio", ".3f"),
        ("Sortino Ratio", "sortino_ratio", ".3f"),
        ("Max Drawdown (%)", "max_drawdown_pct", ".1f"),
        ("Calmar Ratio", "calmar_ratio", ".3f"),
        ("Win Rate (%)", "win_rate_pct", ".1f"),
        ("Profit Factor", "profit_factor", ".2f"),
    ]
    for label, key, fmt in rows:
        sv = metrics_strat.get(key, 0)
        bv = metrics_bh.get(key, 0)
        print(f"{label:<30} {sv:>15{fmt}} {bv:>15{fmt}}")

    print(f"\n{'Backtest period (years)':<30} {metrics_strat.get('years', 0):>15.1f}")
    print(f"{'Num position changes':<30} {metrics_strat.get('num_trades', 0):>15d}")

    print(f"\nOptimal Parameters:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")

    print(f"\nTop 5 Parameter Sets by Sharpe (from grid search):")
    top = grid_df.head(5)
    for i, row in top.iterrows():
        print(
            f"  #{i+1}: Sharpe={row['sharpe_ratio']:.3f}  CAGR={row['cagr_pct']:.1f}%  "
            f"MaxDD={row['max_drawdown_pct']:.1f}%  "
            f"fast={int(row['fast_ema'])} slow={int(row['slow_ema'])} "
            f"trend={int(row['trend_ema'])} donch={int(row['donchian_window'])} "
            f"smooth={int(row['signal_smooth'])}"
        )

    print("\n" + "=" * 72)


def main():
    # 1. Load data
    print("=" * 72)
    print("  STEP 1: Loading GLD price data")
    print("=" * 72)
    df = load_gld_data()
    print(f"  Data: {df['Date'].iloc[0].date()} to {df['Date'].iloc[-1].date()} ({len(df)} bars)")

    # 2. Grid search optimisation
    print("\n" + "=" * 72)
    print("  STEP 2: Grid Search Optimisation")
    print("=" * 72)
    grid_df = grid_search(df)

    # 3. Differential evolution refinement
    print("\n" + "=" * 72)
    print("  STEP 3: Differential Evolution Refinement")
    print("=" * 72)
    de_result = scipy_optimize(df)

    # Pick the best from grid + DE using score (Sharpe + penalties/bonuses)
    best_grid_score = grid_df.iloc[0]["score"]
    de_score = de_result["score"]
    if de_score > best_grid_score:
        best_params = de_result["params"]
        print(f"\n  DE found better params (score {de_score:.3f} > {best_grid_score:.3f})")
    else:
        row = grid_df.iloc[0]
        best_params = {
            "fast_ema": int(row["fast_ema"]),
            "slow_ema": int(row["slow_ema"]),
            "trend_ema": int(row["trend_ema"]),
            "donchian_window": int(row["donchian_window"]),
            "roc_period": int(row["roc_period"]),
            "signal_smooth": int(row["signal_smooth"]),
            "long_threshold": float(row["long_threshold"]),
            "short_threshold": float(row["short_threshold"]),
            "vol_target": float(row["vol_target"]),
            "dd_limit": float(row["dd_limit"]),
            "min_holding": int(row["min_holding"]),
            "transaction_cost_bps": float(row["transaction_cost_bps"]),
        }
        print(f"\n  Grid search found best params (score {best_grid_score:.3f} >= DE {de_score:.3f})")

    # 4. Final backtest with best params
    print("\n" + "=" * 72)
    print("  STEP 4: Final Backtest with Optimal Parameters")
    print("=" * 72)
    strat = TrendFollowingStrategy(**best_params)
    result_df = strat.backtest(df)

    metrics_strat = TrendFollowingStrategy.performance_metrics(
        result_df["strategy_return_net"], name="Trend Strategy"
    )
    metrics_strat["num_trades"] = int((result_df["position"].diff().abs() > 0).sum())

    metrics_bh = TrendFollowingStrategy.performance_metrics(
        result_df["asset_return"], name="Buy & Hold"
    )

    # 5. Walk-forward validation
    print("\n" + "=" * 72)
    print("  STEP 5: Walk-Forward Out-of-Sample Validation")
    print("=" * 72)
    oos_df = walk_forward_validation(df, best_params, n_splits=5)

    # 6. Report
    print_report(metrics_strat, metrics_bh, best_params, grid_df)

    # 7. Charts
    print("\n  Generating charts...")
    plot_results(result_df, best_params, metrics_strat, oos_df)

    # Save optimisation results
    grid_df.to_csv("optimisation_results.csv", index=False)
    print("  Optimisation results saved to optimisation_results.csv")

    # Save final backtest
    result_df.to_csv("backtest_results.csv", index=False)
    print("  Backtest results saved to backtest_results.csv")


if __name__ == "__main__":
    main()
