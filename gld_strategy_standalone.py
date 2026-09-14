#!/usr/bin/env python3
"""
GLD Trend-Following Strategy — Self-Contained Script
=====================================================
Download real daily GLD data via yfinance, optimise, backtest, and report.

Requirements:
    pip install pandas numpy matplotlib scipy yfinance

Usage:
    python gld_strategy_standalone.py

    # Or supply your own CSV (must have columns: Date, Open, High, Low, Close, Volume):
    python gld_strategy_standalone.py --csv /path/to/gld_data.csv
"""

import sys
import argparse
import itertools
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import differential_evolution


# ==========================================================================
# DATA LOADING
# ==========================================================================

def load_data_yfinance(ticker: str = "GLD", start: str = "2004-11-18") -> pd.DataFrame:
    """Download daily OHLCV via yfinance."""
    import yfinance as yf
    df = yf.download(ticker, start=start, auto_adjust=False, progress=False)
    df = df.reset_index()
    # Handle multi-level columns from newer yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if c[1] == "" else c[0] for c in df.columns]
    df = df.rename(columns={"Adj Close": "Adj_Close"})
    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
    if "Adj_Close" in df.columns:
        df["Adj_Close"] = df["Adj_Close"]
    else:
        df["Adj_Close"] = df["Close"]
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)
    return df


def load_data_csv(path: str) -> pd.DataFrame:
    """Load OHLCV from a local CSV file."""
    df = pd.read_csv(path, parse_dates=["Date"])
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col not in df.columns:
            raise ValueError(f"CSV must have column '{col}'. Found: {list(df.columns)}")
    if "Adj_Close" not in df.columns:
        df["Adj_Close"] = df["Close"]
    df = df.dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)
    return df


def load_data(csv_path: str | None = None) -> pd.DataFrame:
    if csv_path:
        print(f"Loading data from CSV: {csv_path}")
        return load_data_csv(csv_path)
    try:
        print("Downloading GLD data via yfinance...")
        df = load_data_yfinance()
        print(f"  Downloaded {len(df)} rows")
        return df
    except Exception as e:
        print(f"yfinance failed: {e}")
        print("Please install yfinance (pip install yfinance) or supply --csv")
        sys.exit(1)


# ==========================================================================
# TECHNICAL INDICATORS
# ==========================================================================

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def atr(high, low, close, window=14):
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    return tr.ewm(span=window, adjust=False).mean()

def donchian_upper(high, window): return high.rolling(window).max()
def donchian_lower(low, window):  return low.rolling(window).min()
def roc(series, period):          return series / series.shift(period) - 1


# ==========================================================================
# STRATEGY
# ==========================================================================

class TrendFollowingStrategy:
    def __init__(self, fast_ema=10, slow_ema=50, trend_ema=200,
                 macd_fast=12, macd_slow=26, macd_signal=9,
                 donchian_window=55, roc_period=60, atr_window=20,
                 signal_smooth=3, long_threshold=0.15, short_threshold=-0.15,
                 vol_target=0.16, dd_limit=0.15, min_holding=3,
                 transaction_cost_bps=5.0):
        self.fast_ema = fast_ema;  self.slow_ema = slow_ema;  self.trend_ema = trend_ema
        self.macd_fast = macd_fast;  self.macd_slow = macd_slow;  self.macd_signal = macd_signal
        self.donchian_window = donchian_window;  self.roc_period = roc_period
        self.atr_window = atr_window;  self.signal_smooth = signal_smooth
        self.long_threshold = long_threshold;  self.short_threshold = short_threshold
        self.vol_target = vol_target;  self.dd_limit = dd_limit
        self.min_holding = min_holding;  self.transaction_cost_bps = transaction_cost_bps

    def compute_signals(self, df):
        d = df.copy()
        close, high, low = d["Close"], d["High"], d["Low"]

        # 1) EMA crossover → continuous (tanh-normalised spread)
        d["fast_ema"] = ema(close, self.fast_ema)
        d["slow_ema"] = ema(close, self.slow_ema)
        d["ema_signal"] = np.tanh((d["fast_ema"] - d["slow_ema"]) / d["slow_ema"] * 100)

        # 2) Trend filter: price vs long-term EMA
        d["trend_ema"] = ema(close, self.trend_ema)
        d["trend_signal"] = np.tanh((close - d["trend_ema"]) / d["trend_ema"] * 20)

        # 3) MACD histogram (z-scored)
        macd_line = ema(close, self.macd_fast) - ema(close, self.macd_slow)
        signal_line = ema(macd_line, self.macd_signal)
        hist = macd_line - signal_line
        hmean = hist.rolling(63).mean();  hstd = hist.rolling(63).std().replace(0, np.nan)
        d["macd_z"] = ((hist - hmean) / hstd).clip(-2, 2) / 2

        # 4) Donchian breakout (persistent)
        d["don_upper"] = donchian_upper(high, self.donchian_window)
        d["don_lower"] = donchian_lower(low, self.donchian_window)
        d["don_signal"] = 0.0
        d.loc[close >= d["don_upper"].shift(1), "don_signal"] = 1.0
        d.loc[close <= d["don_lower"].shift(1), "don_signal"] = -1.0
        d["don_signal"] = d["don_signal"].replace(0, np.nan).ffill().fillna(0)

        # 5) Rate-of-change momentum (z-scored)
        d["roc"] = roc(close, self.roc_period)
        rm = d["roc"].rolling(126).mean();  rs = d["roc"].rolling(126).std().replace(0, np.nan)
        d["roc_signal"] = ((d["roc"] - rm) / rs).clip(-2, 2) / 2

        # 6) Vol regime dampener
        d["realised_vol"] = close.pct_change().rolling(20).std() * np.sqrt(252)
        vol_med = d["realised_vol"].rolling(252).median()
        d["vol_regime"] = np.where(d["realised_vol"] > vol_med * 1.5, 0.5,
                          np.where(d["realised_vol"] > vol_med * 1.2, 0.75, 1.0))

        # Composite signal (weighted)
        d["raw_signal"] = (
            0.25 * d["ema_signal"] + 0.15 * d["trend_signal"]
            + 0.15 * d["macd_z"].fillna(0) + 0.25 * d["don_signal"]
            + 0.20 * d["roc_signal"].fillna(0)
        ) * d["vol_regime"]

        d["smooth_signal"] = d["raw_signal"].rolling(self.signal_smooth).mean()

        # Discretise
        d["target_position"] = np.where(
            d["smooth_signal"] > self.long_threshold, 1.0,
            np.where(d["smooth_signal"] < self.short_threshold, -1.0, 0.0))

        # Min holding period
        d["position"] = self._apply_min_holding(d["target_position"].values, self.min_holding)

        # Vol targeting
        if self.vol_target > 0:
            dvt = self.vol_target / np.sqrt(252)
            dvr = close.pct_change().ewm(span=20).std()
            vs = (dvt / dvr).clip(0.2, 2.0)
            d["position"] = (d["position"] * vs).clip(-1.5, 1.5)
        return d

    @staticmethod
    def _apply_min_holding(positions, min_hold):
        result = positions.copy();  hold = 0;  cur = 0.0
        for i in range(len(result)):
            if result[i] != cur:
                if hold >= min_hold or cur == 0.0:  cur = result[i];  hold = 1
                else:  result[i] = cur;  hold += 1
            else: hold += 1
        return pd.Series(result)

    def backtest(self, df):
        d = self.compute_signals(df)
        d["asset_return"] = d["Close"].pct_change()
        d["strategy_return"] = d["position"].shift(1) * d["asset_return"]

        # Drawdown control
        if self.dd_limit > 0:
            cum = (1 + d["strategy_return"].fillna(0)).cumprod()
            dd = (cum - cum.cummax()) / cum.cummax()
            d["strategy_return"] = d["strategy_return"] * (1 + dd / self.dd_limit).clip(0, 1)

        d["turnover"] = d["position"].diff().abs()
        tc = self.transaction_cost_bps / 10_000
        d["strategy_return_net"] = d["strategy_return"] - d["turnover"].shift(1).fillna(0) * tc
        d["cum_asset"] = (1 + d["asset_return"]).cumprod()
        d["cum_strategy"] = (1 + d["strategy_return_net"]).cumprod()
        return d

    @staticmethod
    def performance_metrics(returns, name="Strategy"):
        r = returns.dropna();  n = len(r)
        if n < 2: return {}
        total = (1 + r).prod() - 1;  years = n / 252
        cagr = (1 + total) ** (1 / years) - 1 if years > 0 else 0
        vol = r.std() * np.sqrt(252);  sharpe = cagr / vol if vol > 0 else 0
        down = r[r < 0].std() * np.sqrt(252);  sortino = cagr / down if down > 0 else 0
        cum = (1 + r).cumprod();  dd = ((cum - cum.cummax()) / cum.cummax()).min()
        calmar = cagr / abs(dd) if dd != 0 else 0
        gp = r[r > 0].sum();  gl = abs(r[r < 0].sum())
        pf = gp / gl if gl > 0 else np.inf
        return {"name": name, "total_return_pct": total*100, "cagr_pct": cagr*100,
                "ann_volatility_pct": vol*100, "sharpe_ratio": sharpe, "sortino_ratio": sortino,
                "max_drawdown_pct": dd*100, "calmar_ratio": calmar,
                "win_rate_pct": (r > 0).sum()/n*100, "profit_factor": pf,
                "num_trades": 0, "years": years}


# ==========================================================================
# OPTIMISATION
# ==========================================================================

def _evaluate(params, df):
    s = TrendFollowingStrategy(**params);  res = s.backtest(df)
    m = TrendFollowingStrategy.performance_metrics(res["strategy_return_net"])
    m["num_trades"] = int((res["position"].diff().abs() > 0).sum())
    return m

def _score(m):
    sh = m.get("sharpe_ratio", -10);  dd = abs(m.get("max_drawdown_pct", -100))
    return sh - max(0, dd - 30) * 0.01 + m.get("cagr_pct", 0) * 0.005

def grid_search(df, verbose=True):
    grid = {
        "fast_ema": [5, 10, 20], "slow_ema": [30, 50, 80], "trend_ema": [150, 200],
        "donchian_window": [20, 55, 80], "roc_period": [40, 60],
        "signal_smooth": [3, 5], "long_threshold": [0.10, 0.20],
        "vol_target": [0.12, 0.16], "dd_limit": [0.10, 0.15],
        "min_holding": [3, 5], "transaction_cost_bps": [5.0],
    }
    keys = list(grid.keys());  combos = list(itertools.product(*grid.values()))
    valid = []
    for vals in combos:
        p = dict(zip(keys, vals))
        if p["fast_ema"] >= p["slow_ema"] or p["slow_ema"] >= p["trend_ema"]: continue
        p["short_threshold"] = -p["long_threshold"];  valid.append(p)
    if verbose: print(f"Grid search: {len(valid)} combinations")
    results = []
    for i, p in enumerate(valid):
        m = _evaluate(p, df);  m["score"] = _score(m);  m.update(p);  results.append(m)
        if verbose and (i+1) % 100 == 0: print(f"  ... {i+1}/{len(valid)}")
    rdf = pd.DataFrame(results).sort_values("score", ascending=False).reset_index(drop=True)
    if verbose and len(rdf) > 0:
        b = rdf.iloc[0]
        print(f"Grid done. Best: Sharpe={b['sharpe_ratio']:.3f} CAGR={b['cagr_pct']:.1f}% MaxDD={b['max_drawdown_pct']:.1f}%")
    return rdf

def de_optimize(df, verbose=True):
    bounds = [(5,25),(30,120),(120,300),(15,100),(20,120),(1,7),(0.05,0.30),(0.08,0.25),(0.08,0.25),(2,8)]
    def obj(x):
        p = {"fast_ema":int(round(x[0])),"slow_ema":int(round(x[1])),"trend_ema":int(round(x[2])),
             "donchian_window":int(round(x[3])),"roc_period":int(round(x[4])),
             "signal_smooth":int(round(x[5])),"long_threshold":round(x[6],3),
             "short_threshold":-round(x[6],3),"vol_target":round(x[7],3),
             "dd_limit":round(x[8],3),"min_holding":int(round(x[9])),"transaction_cost_bps":5.0}
        if p["fast_ema"]>=p["slow_ema"] or p["slow_ema"]>=p["trend_ema"]: return 10.0
        return -_score(_evaluate(p, df))
    if verbose: print("Running differential evolution...")
    res = differential_evolution(obj, bounds, maxiter=80, popsize=25, tol=1e-5, seed=42, polish=False)
    bp = {"fast_ema":int(round(res.x[0])),"slow_ema":int(round(res.x[1])),"trend_ema":int(round(res.x[2])),
          "donchian_window":int(round(res.x[3])),"roc_period":int(round(res.x[4])),
          "signal_smooth":int(round(res.x[5])),"long_threshold":round(res.x[6],3),
          "short_threshold":-round(res.x[6],3),"vol_target":round(res.x[7],3),
          "dd_limit":round(res.x[8],3),"min_holding":int(round(res.x[9])),"transaction_cost_bps":5.0}
    if verbose: print(f"DE best score: {-res.fun:.3f}  params: {bp}")
    return {"params": bp, "score": -res.fun}

def walk_forward(df, params, n_splits=5):
    n = len(df);  results = []
    for i in range(n_splits):
        te = int(n*(0.4+i*0.12));  tend = min(te+int(n*0.15), n)
        if te >= n or tend <= te: continue
        tdf = df.iloc[te:tend].copy().reset_index(drop=True)
        if len(tdf) < 60: continue
        m = _evaluate(params, tdf);  m["fold"] = i+1
        m["test_start"] = df.iloc[te]["Date"].strftime("%Y-%m-%d")
        m["test_end"] = df.iloc[min(tend,n)-1]["Date"].strftime("%Y-%m-%d")
        results.append(m)
    rdf = pd.DataFrame(results)
    if len(rdf) > 0:
        print("\n=== Walk-Forward OOS Validation ===")
        for _, r in rdf.iterrows():
            print(f"  Fold {int(r['fold'])}: {r['test_start']} to {r['test_end']} | "
                  f"Sharpe={r['sharpe_ratio']:.2f}  CAGR={r['cagr_pct']:.1f}%  MaxDD={r['max_drawdown_pct']:.1f}%")
        print(f"  Mean OOS Sharpe: {rdf['sharpe_ratio'].mean():.3f} (+/- {rdf['sharpe_ratio'].std():.3f})")
    return rdf


# ==========================================================================
# CHARTING
# ==========================================================================

def plot_results(df, params, metrics):
    fig = plt.figure(figsize=(18, 22));  gs = fig.add_gridspec(5, 2, hspace=0.35, wspace=0.25)

    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(df["Date"], df["cum_asset"], label="Buy & Hold GLD", alpha=0.8)
    ax1.plot(df["Date"], df["cum_strategy"], label="Trend Strategy (net)", linewidth=1.5, color="darkgreen")
    ax1.set_title("Cumulative Returns: Trend Strategy vs Buy & Hold", fontweight="bold")
    ax1.set_ylabel("Growth of $1");  ax1.legend();  ax1.grid(True, alpha=0.3);  ax1.set_yscale("log")

    ax2 = fig.add_subplot(gs[1, :])
    cum = (1 + df["strategy_return_net"]).cumprod()
    dd = (cum - cum.cummax()) / cum.cummax() * 100
    ax2.fill_between(df["Date"], dd, 0, color="red", alpha=0.3)
    ax2.plot(df["Date"], dd, color="darkred", linewidth=0.8)
    ax2.set_title("Strategy Drawdown", fontweight="bold");  ax2.set_ylabel("Drawdown (%)");  ax2.grid(True, alpha=0.3)

    ax3 = fig.add_subplot(gs[2, :])
    ax3.fill_between(df["Date"], df["position"], 0, where=df["position"]>0, color="green", alpha=0.3, label="Long")
    ax3.fill_between(df["Date"], df["position"], 0, where=df["position"]<0, color="red", alpha=0.3, label="Short")
    ax3.set_title("Position Over Time", fontweight="bold");  ax3.legend();  ax3.grid(True, alpha=0.3)

    ax4 = fig.add_subplot(gs[3, 0])
    rs = df["strategy_return_net"].rolling(252).mean() / df["strategy_return_net"].rolling(252).std() * np.sqrt(252)
    ax4.plot(df["Date"], rs, color="navy");  ax4.axhline(0, color="red", ls="--", alpha=0.5)
    ax4.axhline(metrics["sharpe_ratio"], color="green", ls="--", alpha=0.5, label=f'Sharpe={metrics["sharpe_ratio"]:.2f}')
    ax4.set_title("Rolling 1-Year Sharpe");  ax4.legend(fontsize=8);  ax4.grid(True, alpha=0.3)

    ax5 = fig.add_subplot(gs[3, 1])
    mo = df.set_index("Date")["strategy_return_net"].resample("ME").apply(lambda x:(1+x).prod()-1)*100
    mdf = pd.DataFrame({"Year":mo.index.year,"Month":mo.index.month,"Return":mo.values})
    piv = mdf.pivot_table(index="Year",columns="Month",values="Return",aggfunc="mean")
    if len(piv)>10: piv=piv.iloc[-10:]
    im = ax5.imshow(piv.values, cmap="RdYlGn", aspect="auto", vmin=-8, vmax=8)
    ax5.set_xticks(range(12));  ax5.set_xticklabels(["J","F","M","A","M","J","J","A","S","O","N","D"],fontsize=7)
    ax5.set_yticks(range(len(piv)));  ax5.set_yticklabels(piv.index,fontsize=7)
    ax5.set_title("Monthly Returns Heatmap (%)");  plt.colorbar(im,ax=ax5,shrink=0.8)

    ax6 = fig.add_subplot(gs[4, 0])
    ax6.plot(df["Date"].iloc[-504:], df["smooth_signal"].iloc[-504:], color="purple")
    lt=params.get("long_threshold",0.15); st=params.get("short_threshold",-0.15)
    ax6.axhline(lt,color="green",ls="--",alpha=0.4,label=f"Long ({lt})")
    ax6.axhline(st,color="red",ls="--",alpha=0.4,label=f"Short ({st})")
    ax6.set_title("Composite Signal (Last 2 Years)");  ax6.legend(fontsize=7);  ax6.grid(True,alpha=0.3)

    ax7 = fig.add_subplot(gs[4, 1])
    ays = df.set_index("Date")["strategy_return_net"].resample("YE").apply(lambda x:(1+x).prod()-1)*100
    aya = df.set_index("Date")["asset_return"].resample("YE").apply(lambda x:(1+x).prod()-1)*100
    yrs = ays.index.year;  x = np.arange(len(yrs));  w=0.35
    ax7.bar(x-w/2,aya.values,w,label="Buy & Hold",alpha=0.7,color="steelblue")
    ax7.bar(x+w/2,ays.values,w,label="Strategy",alpha=0.7,color="darkgreen")
    ax7.set_xticks(x);  ax7.set_xticklabels(yrs,rotation=45,fontsize=7)
    ax7.set_title("Annual Returns (%)");  ax7.legend(fontsize=8);  ax7.grid(True,alpha=0.3,axis="y")

    plt.savefig("gld_strategy_report.png", dpi=150, bbox_inches="tight")
    print("\nChart saved to gld_strategy_report.png");  plt.close()


# ==========================================================================
# MAIN
# ==========================================================================

def main():
    parser = argparse.ArgumentParser(description="GLD Trend-Following Strategy")
    parser.add_argument("--csv", type=str, default=None, help="Path to CSV with Date,Open,High,Low,Close,Volume")
    args = parser.parse_args()

    # 1. Load data
    print("=" * 72);  print("  STEP 1: Loading GLD price data");  print("=" * 72)
    df = load_data(args.csv)
    print(f"  Data: {df['Date'].iloc[0].date()} to {df['Date'].iloc[-1].date()} ({len(df)} bars)")
    ann_vol = df["Close"].pct_change().std() * np.sqrt(252)
    print(f"  Annualised vol: {ann_vol:.1%}")

    # 2. Grid search
    print("\n" + "=" * 72);  print("  STEP 2: Grid Search");  print("=" * 72)
    gdf = grid_search(df)

    # 3. Differential evolution
    print("\n" + "=" * 72);  print("  STEP 3: Differential Evolution");  print("=" * 72)
    de = de_optimize(df)

    # Pick best
    gs_score = gdf.iloc[0]["score"];  de_score = de["score"]
    if de_score > gs_score:
        best = de["params"];  print(f"\n  DE wins (score {de_score:.3f} > {gs_score:.3f})")
    else:
        r = gdf.iloc[0]
        best = {k: int(r[k]) if k in ["fast_ema","slow_ema","trend_ema","donchian_window",
                "roc_period","signal_smooth","min_holding"] else float(r[k])
                for k in ["fast_ema","slow_ema","trend_ema","donchian_window","roc_period",
                "signal_smooth","long_threshold","short_threshold","vol_target","dd_limit",
                "min_holding","transaction_cost_bps"]}
        print(f"\n  Grid wins (score {gs_score:.3f} >= {de_score:.3f})")

    # 4. Final backtest
    print("\n" + "=" * 72);  print("  STEP 4: Final Backtest");  print("=" * 72)
    strat = TrendFollowingStrategy(**best)
    result = strat.backtest(df)
    ms = TrendFollowingStrategy.performance_metrics(result["strategy_return_net"], "Strategy")
    ms["num_trades"] = int((result["position"].diff().abs() > 0).sum())
    mb = TrendFollowingStrategy.performance_metrics(result["asset_return"], "Buy & Hold")

    # 5. Walk-forward
    print("\n" + "=" * 72);  print("  STEP 5: Walk-Forward Validation");  print("=" * 72)
    walk_forward(df, best)

    # 6. Report
    print("\n" + "=" * 72)
    print("       GLD TREND-FOLLOWING STRATEGY — PERFORMANCE REPORT")
    print("=" * 72)
    print(f"\n{'Metric':<30} {'Strategy':>15} {'Buy & Hold':>15}")
    print("-" * 62)
    for label, key, fmt in [
        ("Total Return (%)", "total_return_pct", ".1f"),
        ("CAGR (%)", "cagr_pct", ".1f"),
        ("Ann. Volatility (%)", "ann_volatility_pct", ".1f"),
        ("Sharpe Ratio", "sharpe_ratio", ".3f"),
        ("Sortino Ratio", "sortino_ratio", ".3f"),
        ("Max Drawdown (%)", "max_drawdown_pct", ".1f"),
        ("Calmar Ratio", "calmar_ratio", ".3f"),
        ("Win Rate (%)", "win_rate_pct", ".1f"),
        ("Profit Factor", "profit_factor", ".2f"),
    ]:
        print(f"{label:<30} {ms.get(key,0):>15{fmt}} {mb.get(key,0):>15{fmt}}")
    print(f"\n{'Period (years)':<30} {ms.get('years',0):>15.1f}")
    print(f"{'Position changes':<30} {ms.get('num_trades',0):>15d}")
    print(f"\nOptimal Parameters:")
    for k, v in best.items(): print(f"  {k}: {v}")
    print("=" * 72)

    # 7. Charts
    print("\n  Generating charts...")
    plot_results(result, best, ms)

    # Save
    gdf.to_csv("optimisation_results.csv", index=False)
    result.to_csv("backtest_results.csv", index=False)
    print("  Results saved to optimisation_results.csv and backtest_results.csv")


if __name__ == "__main__":
    main()
