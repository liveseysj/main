"""
Parameter optimisation for the GLD trend-following strategy.

Approaches:
  1. Grid search over key parameter combinations
  2. scipy.optimize.differential_evolution for continuous refinement

Objective: maximise risk-adjusted returns (Sharpe with drawdown penalty).
Includes walk-forward validation to guard against overfitting.
"""

import itertools
import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution

from strategy import TrendFollowingStrategy


def _evaluate(params: dict, df: pd.DataFrame) -> dict:
    """Run a backtest with given params and return metrics."""
    strat = TrendFollowingStrategy(**params)
    result = strat.backtest(df)
    metrics = TrendFollowingStrategy.performance_metrics(
        result["strategy_return_net"], name="opt"
    )
    metrics["num_trades"] = int((result["position"].diff().abs() > 0).sum())
    return metrics


def _objective_score(metrics: dict) -> float:
    """Combined objective: Sharpe ratio with drawdown penalty."""
    sharpe = metrics.get("sharpe_ratio", -10)
    max_dd = abs(metrics.get("max_drawdown_pct", -100))
    cagr = metrics.get("cagr_pct", 0)

    # Penalise drawdowns beyond -30%
    dd_penalty = max(0, max_dd - 30) * 0.01

    # Reward higher CAGR as tiebreaker
    cagr_bonus = cagr * 0.005

    return sharpe - dd_penalty + cagr_bonus


def grid_search(
    df: pd.DataFrame,
    param_grid: dict | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Exhaustive grid search over parameter combinations.
    Returns a DataFrame of all results sorted by objective score.
    """
    if param_grid is None:
        param_grid = {
            "fast_ema": [5, 10, 20],
            "slow_ema": [30, 50, 80],
            "trend_ema": [150, 200],
            "donchian_window": [20, 55, 80],
            "roc_period": [40, 60],
            "signal_smooth": [3, 5],
            "long_threshold": [0.10, 0.20],
            "vol_target": [0.12, 0.16],
            "dd_limit": [0.10, 0.15],
            "min_holding": [3, 5],
            "transaction_cost_bps": [5.0],
        }

    keys = list(param_grid.keys())
    combos = list(itertools.product(*param_grid.values()))

    # Filter invalid combos upfront
    valid_combos = []
    for vals in combos:
        params = dict(zip(keys, vals))
        if params.get("fast_ema", 0) >= params.get("slow_ema", 999):
            continue
        if params.get("slow_ema", 0) >= params.get("trend_ema", 999):
            continue
        # Mirror thresholds: short_threshold = -long_threshold
        params["short_threshold"] = -params["long_threshold"]
        valid_combos.append(params)

    if verbose:
        print(f"Grid search: {len(valid_combos)} valid parameter combinations (from {len(combos)} total)")

    results = []
    for i, params in enumerate(valid_combos):
        metrics = _evaluate(params, df)
        metrics["score"] = _objective_score(metrics)
        metrics.update(params)
        results.append(metrics)

        if verbose and (i + 1) % 100 == 0:
            print(f"  ... {i + 1}/{len(valid_combos)} evaluated")

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values("score", ascending=False).reset_index(drop=True)
    if verbose and len(results_df) > 0:
        best = results_df.iloc[0]
        print(f"Grid search complete. Best score: {best['score']:.3f} (Sharpe={best['sharpe_ratio']:.3f}, CAGR={best['cagr_pct']:.1f}%, MaxDD={best['max_drawdown_pct']:.1f}%)")
    return results_df


def scipy_optimize(
    df: pd.DataFrame,
    verbose: bool = True,
) -> dict:
    """
    Use differential evolution to find the optimal continuous parameters.
    Returns best parameter dict and its score.
    """

    bounds = [
        (5, 25),      # fast_ema
        (30, 120),    # slow_ema
        (120, 300),   # trend_ema
        (15, 100),    # donchian_window
        (20, 120),    # roc_period
        (1, 7),       # signal_smooth
        (0.05, 0.30), # long_threshold
        (0.08, 0.25), # vol_target
        (0.08, 0.25), # dd_limit
        (2, 8),       # min_holding
    ]

    def objective(x):
        params = {
            "fast_ema": int(round(x[0])),
            "slow_ema": int(round(x[1])),
            "trend_ema": int(round(x[2])),
            "donchian_window": int(round(x[3])),
            "roc_period": int(round(x[4])),
            "signal_smooth": int(round(x[5])),
            "long_threshold": round(x[6], 3),
            "short_threshold": -round(x[6], 3),
            "vol_target": round(x[7], 3),
            "dd_limit": round(x[8], 3),
            "min_holding": int(round(x[9])),
            "transaction_cost_bps": 5.0,
        }
        if params["fast_ema"] >= params["slow_ema"]:
            return 10.0
        if params["slow_ema"] >= params["trend_ema"]:
            return 10.0

        metrics = _evaluate(params, df)
        score = _objective_score(metrics)
        return -score

    if verbose:
        print("Running differential evolution optimisation...")

    result = differential_evolution(
        objective,
        bounds,
        maxiter=80,
        popsize=25,
        tol=1e-5,
        seed=42,
        polish=False,
    )

    best_params = {
        "fast_ema": int(round(result.x[0])),
        "slow_ema": int(round(result.x[1])),
        "trend_ema": int(round(result.x[2])),
        "donchian_window": int(round(result.x[3])),
        "roc_period": int(round(result.x[4])),
        "signal_smooth": int(round(result.x[5])),
        "long_threshold": round(result.x[6], 3),
        "short_threshold": -round(result.x[6], 3),
        "vol_target": round(result.x[7], 3),
        "dd_limit": round(result.x[8], 3),
        "min_holding": int(round(result.x[9])),
        "transaction_cost_bps": 5.0,
    }

    if verbose:
        print(f"Best score (DE): {-result.fun:.3f}")
        print(f"Best params: {best_params}")

    return {"params": best_params, "score": -result.fun}


def walk_forward_validation(
    df: pd.DataFrame,
    params: dict,
    n_splits: int = 5,
    train_pct: float = 0.6,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Walk-forward (expanding window) out-of-sample validation.
    Tests that the strategy generalises beyond the optimisation period.
    """
    n = len(df)
    results = []

    for i in range(n_splits):
        # Expanding train window, fixed-size test windows
        train_end = int(n * (0.4 + i * 0.12))
        test_end = min(train_end + int(n * 0.15), n)

        if train_end >= n or test_end <= train_end:
            continue

        test_df = df.iloc[train_end:test_end].copy().reset_index(drop=True)

        if len(test_df) < 60:
            continue

        metrics = _evaluate(params, test_df)
        metrics["fold"] = i + 1
        metrics["test_size"] = len(test_df)
        metrics["test_start"] = df.iloc[train_end]["Date"].strftime("%Y-%m-%d")
        metrics["test_end"] = df.iloc[min(test_end, n) - 1]["Date"].strftime("%Y-%m-%d")
        results.append(metrics)

    results_df = pd.DataFrame(results)
    if verbose and len(results_df) > 0:
        print("\n=== Walk-Forward Validation ===")
        for _, row in results_df.iterrows():
            print(
                f"  Fold {int(row['fold'])}: "
                f"{row['test_start']} to {row['test_end']} | "
                f"Sharpe={row['sharpe_ratio']:.2f}  "
                f"CAGR={row['cagr_pct']:.1f}%  "
                f"MaxDD={row['max_drawdown_pct']:.1f}%"
            )
        mean_sharpe = results_df["sharpe_ratio"].mean()
        std_sharpe = results_df["sharpe_ratio"].std()
        print(f"  Mean OOS Sharpe: {mean_sharpe:.3f} (+/- {std_sharpe:.3f})")

    return results_df
