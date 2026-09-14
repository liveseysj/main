"""
Fetch historical GLD (SPDR Gold Shares ETF) price data.

Priority order:
  1. Yahoo Finance direct download (daily OHLCV)
  2. World Bank monthly gold prices from GitHub → interpolated to daily
  3. Fully synthetic fallback
"""
import urllib.request
import urllib.error
import csv
import io
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime


def fetch_gld_data(
    ticker: str = "GLD",
    start: str = "2004-11-18",  # GLD inception date
    end: str | None = None,
) -> pd.DataFrame:
    """Download daily OHLCV data for *ticker* from Yahoo Finance."""

    if end is None:
        end = datetime.today().strftime("%Y-%m-%d")

    period1 = int(datetime.strptime(start, "%Y-%m-%d").timestamp())
    period2 = int(datetime.strptime(end, "%Y-%m-%d").timestamp())

    url = (
        f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}"
        f"?period1={period1}&period2={period2}"
        f"&interval=1d&events=history&includeAdjustedClose=true"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    # Try the CSV download endpoint first
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
            df = pd.read_csv(io.StringIO(raw), parse_dates=["Date"])
            df = df.sort_values("Date").reset_index(drop=True)
            df = df.rename(columns={"Adj Close": "Adj_Close"})
            df = df.dropna(subset=["Close", "Volume"])
            print(f"Fetched {len(df)} rows for {ticker} from Yahoo Finance CSV endpoint.")
            return df
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed ({e}), retrying...")
            time.sleep(2 ** attempt)

    # Fallback: try the v8 chart JSON API
    print("CSV endpoint failed, trying v8 chart API...")
    chart_url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1={period1}&period2={period2}"
        f"&interval=1d&includeAdjustedClose=true"
    )
    for attempt in range(3):
        try:
            req = urllib.request.Request(chart_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]
            adj = result["indicators"]["adjclose"][0]["adjclose"]
            df = pd.DataFrame({
                "Date": pd.to_datetime(timestamps, unit="s").normalize(),
                "Open": quote["open"],
                "High": quote["high"],
                "Low": quote["low"],
                "Close": quote["close"],
                "Adj_Close": adj,
                "Volume": quote["volume"],
            })
            df = df.dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)
            print(f"Fetched {len(df)} rows for {ticker} from v8 chart API.")
            return df
        except Exception as e:
            print(f"  Chart API attempt {attempt + 1} failed ({e}), retrying...")
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Could not download data for {ticker} after multiple attempts.")


def fetch_worldbank_gold() -> pd.DataFrame:
    """
    Fetch real monthly gold prices (USD/oz) from the World Bank dataset
    hosted on GitHub, then interpolate to daily OHLCV to approximate GLD.

    GLD tracks gold at roughly 1/10th of the spot price per share.
    """
    url = "https://raw.githubusercontent.com/datasets/gold-prices/main/data/monthly.csv"
    headers = {"User-Agent": "Mozilla/5.0"}

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
            break
        except Exception as e:
            print(f"  World Bank attempt {attempt + 1} failed ({e}), retrying...")
            time.sleep(2 ** attempt)
    else:
        raise RuntimeError("Could not download World Bank gold prices.")

    # Parse monthly data
    monthly = pd.read_csv(io.StringIO(raw))
    monthly["Date"] = pd.to_datetime(monthly["Date"], format="%Y-%m")
    monthly = monthly.sort_values("Date").reset_index(drop=True)

    # Filter to GLD era: Nov 2004 onwards
    monthly = monthly[monthly["Date"] >= "2004-11-01"].copy()

    # Convert gold spot (USD/oz) to approximate GLD price
    # GLD holds ~1/10 oz of gold per share; at inception (Nov 2004),
    # gold was ~$444/oz and GLD opened at ~$44.4
    # Use a fixed divisor calibrated to GLD inception
    gold_at_inception = monthly.iloc[0]["Price"]
    gld_scale = 44.4 / gold_at_inception  # ≈ 0.1
    monthly["GLD_Price"] = monthly["Price"] * gld_scale

    # Create daily business-day index
    start_date = monthly["Date"].iloc[0]
    end_date = monthly["Date"].iloc[-1] + pd.offsets.MonthEnd(0)
    daily_dates = pd.bdate_range(start=start_date, end=end_date)

    # Interpolate monthly closes to daily (smooth guideline)
    monthly_indexed = monthly.set_index("Date")["GLD_Price"]
    guideline = monthly_indexed.reindex(daily_dates).interpolate(method="cubic")
    guideline = guideline.dropna()

    # --- Add realistic daily noise ---
    # Gold/GLD has annualised vol ~16-20%. Monthly data captures the drift
    # but not the daily noise. We add mean-reverting noise around the
    # monthly path so the daily returns have realistic magnitude.
    np.random.seed(42)
    n = len(guideline)
    guide = guideline.values

    # Compute the monthly-implied daily returns (the smooth trend)
    smooth_ret = np.diff(guide, prepend=guide[0]) / np.maximum(guide, 1e-6)

    # GLD historical daily vol ≈ 1.1% (≈17% annualised / sqrt(252))
    # The smooth interpolation already has some return, so we add noise
    # to bring total daily vol to realistic levels.
    smooth_vol = np.std(smooth_ret[1:])  # vol from interpolation
    target_daily_vol = 0.011  # ~17.5% annualised
    # Noise vol to add (orthogonal): sqrt(target^2 - smooth^2)
    noise_vol = np.sqrt(max(target_daily_vol**2 - smooth_vol**2, 0.005**2))

    # Generate GARCH-like noise (volatility clustering)
    noise = np.zeros(n)
    vol_t = np.full(n, noise_vol)
    for i in range(1, n):
        vol_t[i] = np.sqrt(
            noise_vol**2 * 0.05
            + 0.10 * noise[i - 1] ** 2
            + 0.85 * vol_t[i - 1] ** 2
        )
        noise[i] = vol_t[i] * np.random.standard_normal()

    # Mean-reverting: anchor back to the monthly guideline
    # Each month-end, pull the price back to the known monthly close
    close = np.empty(n)
    close[0] = guide[0]
    cum_noise = 0.0
    reversion_speed = 0.03  # pull 3% of gap per day toward guideline

    for i in range(1, n):
        cum_noise += noise[i]
        # Mean-revert toward guideline
        gap = np.log(guide[i]) - np.log(close[i - 1])
        daily_ret = smooth_ret[i] + noise[i] + reversion_speed * gap
        close[i] = close[i - 1] * np.exp(daily_ret)

    # Generate OHLC with realistic intraday range
    daily_vol = pd.Series(close).pct_change().rolling(20).std().fillna(target_daily_vol).values
    intraday_range = np.maximum(daily_vol * 1.5, 0.003)

    high = close * (1 + intraday_range * np.random.uniform(0.3, 1.0, n))
    low = close * (1 - intraday_range * np.random.uniform(0.3, 1.0, n))
    high = np.maximum(high, close)
    low = np.minimum(low, close)
    opn = low + (high - low) * np.random.uniform(0.25, 0.75, n)

    # Volume: approximate GLD average daily volume (~8M shares)
    volume = np.random.lognormal(mean=np.log(8_000_000), sigma=0.5, size=n).astype(int)

    df = pd.DataFrame({
        "Date": guideline.index,
        "Open": opn,
        "High": high,
        "Low": low,
        "Close": close,
        "Adj_Close": close,
        "Volume": volume,
    })

    print(f"Fetched {len(df)} daily rows from World Bank gold prices (real monthly, interpolated to daily).")
    print(f"  Gold spot range: ${monthly['Price'].iloc[0]:.0f}/oz to ${monthly['Price'].iloc[-1]:.0f}/oz")
    print(f"  GLD-equivalent range: ${df['Close'].iloc[0]:.2f} to ${df['Close'].iloc[-1]:.2f}")
    return df


def generate_synthetic_gld(start: str = "2004-11-18", end: str = "2025-12-31") -> pd.DataFrame:
    """
    Generate realistic synthetic GLD price data as a last-resort fallback.
    Models gold's historical behaviour: long-term uptrend with volatility clusters.
    """
    np.random.seed(42)
    dates = pd.bdate_range(start=start, end=end)
    n = len(dates)

    daily_mu = 0.08 / 252
    daily_sigma = 0.16 / (252 ** 0.5)

    returns = np.zeros(n)
    vol = np.full(n, daily_sigma)
    for i in range(1, n):
        vol[i] = np.sqrt(
            0.00001 + 0.08 * returns[i - 1] ** 2 + 0.90 * vol[i - 1] ** 2
        )
        returns[i] = daily_mu + vol[i] * np.random.standard_normal()

    price = 44.4 * np.exp(np.cumsum(returns))
    high = price * (1 + np.abs(np.random.normal(0, 0.005, n)))
    low = price * (1 - np.abs(np.random.normal(0, 0.005, n)))
    opn = low + (high - low) * np.random.uniform(0.3, 0.7, n)
    volume = np.random.lognormal(mean=17, sigma=0.6, size=n).astype(int)

    df = pd.DataFrame({
        "Date": dates,
        "Open": opn,
        "High": high,
        "Low": low,
        "Close": price,
        "Adj_Close": price,
        "Volume": volume,
    })
    print(f"Generated {len(df)} rows of fully synthetic GLD data ({start} to {end}).")
    return df


def load_gld_data() -> pd.DataFrame:
    """
    Try to fetch real data in priority order:
      1. Yahoo Finance (daily OHLCV)
      2. World Bank gold via GitHub (monthly, interpolated to daily)
      3. Synthetic fallback
    """
    # 1. Try Yahoo Finance
    try:
        return fetch_gld_data()
    except Exception as e:
        print(f"Yahoo Finance failed ({e}).")

    # 2. Try World Bank monthly gold prices
    try:
        print("Trying World Bank gold prices from GitHub...")
        return fetch_worldbank_gold()
    except Exception as e:
        print(f"World Bank gold failed ({e}).")

    # 3. Last resort: synthetic
    print("All live sources failed. Using synthetic data as fallback.")
    return generate_synthetic_gld()


if __name__ == "__main__":
    df = load_gld_data()
    print(df.head(10))
    print(f"\nDate range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"Shape: {df.shape}")
    df.to_csv("gld_data.csv", index=False)
    print("Saved to gld_data.csv")
