"""
GLD Trend-Following Strategy (Long/Short) — Enhanced Version

Signal components:
  1. Dual Moving Average Crossover (fast EMA vs slow EMA)
  2. Price vs long-term EMA (trend filter)
  3. MACD histogram momentum
  4. Donchian channel breakout
  5. Rate-of-change momentum
  6. Volatility regime filter (reduce exposure in high-vol regimes)

Risk management:
  - Volatility targeting (scale position to target annualised vol)
  - Drawdown control (reduce exposure during drawdowns)
  - Signal smoothing to reduce whipsaws
  - Minimum holding period to avoid excessive turnover
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------------------

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=window, adjust=False).mean()


def donchian_upper(high: pd.Series, window: int) -> pd.Series:
    return high.rolling(window).max()


def donchian_lower(low: pd.Series, window: int) -> pd.Series:
    return low.rolling(window).min()


def roc(series: pd.Series, period: int) -> pd.Series:
    """Rate of change (momentum)."""
    return series / series.shift(period) - 1


# ---------------------------------------------------------------------------
# Strategy class
# ---------------------------------------------------------------------------

class TrendFollowingStrategy:
    """
    Enhanced trend-following strategy for a single asset (GLD).

    Parameters
    ----------
    fast_ema : int       – fast EMA period
    slow_ema : int       – slow EMA period
    trend_ema : int      – long-term trend filter EMA
    macd_fast : int      – MACD fast EMA
    macd_slow : int      – MACD slow EMA
    macd_signal : int    – MACD signal line EMA
    donchian_window : int – breakout channel lookback
    roc_period : int     – rate of change lookback
    atr_window : int     – ATR lookback for vol scaling
    signal_smooth : int  – smoothing window for composite signal
    long_threshold : float  – signal threshold to go long
    short_threshold : float – signal threshold to go short
    vol_target : float   – annualised volatility target (0 = off)
    dd_limit : float     – drawdown limit to start reducing (e.g. 0.10 = -10%)
    min_holding : int    – minimum holding period in days
    transaction_cost_bps : float – one-way transaction cost in basis points
    """

    def __init__(
        self,
        fast_ema: int = 10,
        slow_ema: int = 50,
        trend_ema: int = 200,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        donchian_window: int = 55,
        roc_period: int = 60,
        atr_window: int = 20,
        signal_smooth: int = 3,
        long_threshold: float = 0.15,
        short_threshold: float = -0.15,
        vol_target: float = 0.16,
        dd_limit: float = 0.15,
        min_holding: int = 3,
        transaction_cost_bps: float = 5.0,
    ):
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.trend_ema = trend_ema
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.donchian_window = donchian_window
        self.roc_period = roc_period
        self.atr_window = atr_window
        self.signal_smooth = signal_smooth
        self.long_threshold = long_threshold
        self.short_threshold = short_threshold
        self.vol_target = vol_target
        self.dd_limit = dd_limit
        self.min_holding = min_holding
        self.transaction_cost_bps = transaction_cost_bps

    # ------------------------------------------------------------------
    def compute_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all indicators and the composite signal."""
        d = df.copy()
        close = d["Close"]
        high = d["High"]
        low = d["Low"]

        # 1) Dual EMA crossover  → continuous signal based on spread
        d["fast_ema"] = ema(close, self.fast_ema)
        d["slow_ema"] = ema(close, self.slow_ema)
        ema_spread = (d["fast_ema"] - d["slow_ema"]) / d["slow_ema"]
        # Normalise spread to [-1, 1] via tanh scaling
        d["ema_signal"] = np.tanh(ema_spread * 100)

        # 2) Trend filter: price vs long-term EMA  → continuous
        d["trend_ema"] = ema(close, self.trend_ema)
        trend_spread = (close - d["trend_ema"]) / d["trend_ema"]
        d["trend_signal"] = np.tanh(trend_spread * 20)

        # 3) MACD histogram  → normalised to [-1, +1]
        macd_line = ema(close, self.macd_fast) - ema(close, self.macd_slow)
        signal_line = ema(macd_line, self.macd_signal)
        histogram = macd_line - signal_line
        d["macd_hist"] = histogram
        hist_mean = histogram.rolling(63).mean()
        hist_std = histogram.rolling(63).std().replace(0, np.nan)
        d["macd_z"] = ((histogram - hist_mean) / hist_std).clip(-2, 2) / 2

        # 4) Donchian breakout → persistent signal
        d["don_upper"] = donchian_upper(high, self.donchian_window)
        d["don_lower"] = donchian_lower(low, self.donchian_window)
        d["don_signal"] = 0.0
        d.loc[close >= d["don_upper"].shift(1), "don_signal"] = 1.0
        d.loc[close <= d["don_lower"].shift(1), "don_signal"] = -1.0
        d["don_signal"] = d["don_signal"].replace(0, np.nan).ffill().fillna(0)

        # 5) Rate of change momentum → normalised
        d["roc"] = roc(close, self.roc_period)
        roc_mean = d["roc"].rolling(126).mean()
        roc_std = d["roc"].rolling(126).std().replace(0, np.nan)
        d["roc_signal"] = ((d["roc"] - roc_mean) / roc_std).clip(-2, 2) / 2

        # 6) Volatility regime: reduce signal in high-vol environments
        d["atr_val"] = atr(high, low, close, self.atr_window)
        d["realised_vol"] = close.pct_change().rolling(20).std() * np.sqrt(252)
        vol_median = d["realised_vol"].rolling(252).median()
        d["vol_regime"] = np.where(
            d["realised_vol"] > vol_median * 1.5, 0.5,  # high vol → half weight
            np.where(d["realised_vol"] > vol_median * 1.2, 0.75, 1.0)
        )

        # Composite signal: weighted average
        w_cross = 0.25
        w_trend = 0.15
        w_macd = 0.15
        w_donchian = 0.25
        w_roc = 0.20
        d["raw_signal"] = (
            w_cross * d["ema_signal"]
            + w_trend * d["trend_signal"]
            + w_macd * d["macd_z"].fillna(0)
            + w_donchian * d["don_signal"]
            + w_roc * d["roc_signal"].fillna(0)
        )

        # Apply vol regime dampening
        d["raw_signal"] = d["raw_signal"] * d["vol_regime"]

        # Smooth the signal
        d["smooth_signal"] = d["raw_signal"].rolling(self.signal_smooth).mean()

        # Discretise into target position with thresholds
        d["target_position"] = np.where(
            d["smooth_signal"] > self.long_threshold, 1.0,
            np.where(d["smooth_signal"] < self.short_threshold, -1.0, 0.0)
        )

        # Apply minimum holding period
        d["position"] = self._apply_min_holding(d["target_position"].values, self.min_holding)

        # Volatility targeting: scale position size
        if self.vol_target > 0:
            daily_vol_target = self.vol_target / np.sqrt(252)
            daily_realised = close.pct_change().ewm(span=20).std()
            vol_scalar = (daily_vol_target / daily_realised).clip(0.2, 2.0)
            d["vol_scalar"] = vol_scalar
            d["position"] = (d["position"] * vol_scalar).clip(-1.5, 1.5)
        else:
            d["vol_scalar"] = 1.0

        return d

    @staticmethod
    def _apply_min_holding(positions: np.ndarray, min_hold: int) -> pd.Series:
        """Enforce minimum holding period to reduce whipsaws."""
        result = positions.copy()
        hold_counter = 0
        current_pos = 0.0

        for i in range(len(result)):
            if result[i] != current_pos:
                if hold_counter >= min_hold or current_pos == 0.0:
                    current_pos = result[i]
                    hold_counter = 1
                else:
                    result[i] = current_pos
                    hold_counter += 1
            else:
                hold_counter += 1

        return pd.Series(result)

    # ------------------------------------------------------------------
    def backtest(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run the backtest and compute PnL with drawdown control."""
        d = self.compute_signals(df)

        # Daily returns of the underlying
        d["asset_return"] = d["Close"].pct_change()

        # Strategy returns: yesterday's position * today's return
        d["strategy_return"] = d["position"].shift(1) * d["asset_return"]

        # Drawdown control: reduce exposure during strategy drawdowns
        if self.dd_limit > 0:
            cum = (1 + d["strategy_return"].fillna(0)).cumprod()
            running_max = cum.cummax()
            dd = (cum - running_max) / running_max
            # Linear scaling: at dd_limit, scale to 50%; at 2*dd_limit, scale to 0%
            dd_scalar = (1 + dd / self.dd_limit).clip(0.0, 1.0)
            d["strategy_return"] = d["strategy_return"] * dd_scalar

        # Transaction costs: proportional to position change
        d["turnover"] = d["position"].diff().abs()
        tc = self.transaction_cost_bps / 10_000
        d["strategy_return_net"] = d["strategy_return"] - d["turnover"].shift(1).fillna(0) * tc

        # Cumulative
        d["cum_asset"] = (1 + d["asset_return"]).cumprod()
        d["cum_strategy"] = (1 + d["strategy_return_net"]).cumprod()

        return d

    # ------------------------------------------------------------------
    @staticmethod
    def performance_metrics(returns: pd.Series, name: str = "Strategy") -> dict:
        """Compute key performance metrics from a daily return series."""
        r = returns.dropna()
        n = len(r)
        if n < 2:
            return {}

        total_return = (1 + r).prod() - 1
        years = n / 252
        cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        ann_vol = r.std() * np.sqrt(252)
        sharpe = cagr / ann_vol if ann_vol > 0 else 0

        # Sortino (downside deviation)
        downside = r[r < 0].std() * np.sqrt(252)
        sortino = cagr / downside if downside > 0 else 0

        # Max drawdown
        cum = (1 + r).cumprod()
        running_max = cum.cummax()
        drawdown = (cum - running_max) / running_max
        max_dd = drawdown.min()

        # Calmar
        calmar = cagr / abs(max_dd) if max_dd != 0 else 0

        # Win rate
        win_rate = (r > 0).sum() / n

        # Profit factor
        gross_profit = r[r > 0].sum()
        gross_loss = abs(r[r < 0].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

        # Average win/loss
        avg_win = r[r > 0].mean() * 100 if (r > 0).any() else 0
        avg_loss = r[r < 0].mean() * 100 if (r < 0).any() else 0

        return {
            "name": name,
            "total_return_pct": total_return * 100,
            "cagr_pct": cagr * 100,
            "ann_volatility_pct": ann_vol * 100,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown_pct": max_dd * 100,
            "calmar_ratio": calmar,
            "win_rate_pct": win_rate * 100,
            "profit_factor": profit_factor,
            "avg_win_pct": avg_win,
            "avg_loss_pct": avg_loss,
            "num_trades": 0,  # filled externally
            "years": years,
        }
