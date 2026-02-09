"""
Fetch historical GLD (SPDR Gold Shares ETF) price data from Yahoo Finance.
"""
import urllib.request
import urllib.error
import csv
import io
import time
import json
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
            # Drop rows with nulls in critical columns
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


def generate_synthetic_gld(start: str = "2004-11-18", end: str = "2025-12-31") -> pd.DataFrame:
    """
    Generate realistic synthetic GLD price data as a fallback.
    Models gold's historical behaviour: long-term uptrend with volatility clusters.
    """
    import numpy as np

    np.random.seed(42)
    dates = pd.bdate_range(start=start, end=end)
    n = len(dates)

    # GLD started ~$44.4, peaked ~$185 in 2011, dropped to ~$100 in 2015, rose to ~$240 by 2024
    # Annualised return ~8%, annualised vol ~16%
    daily_mu = 0.08 / 252
    daily_sigma = 0.16 / (252 ** 0.5)

    # GARCH-like volatility clustering
    returns = np.zeros(n)
    vol = np.full(n, daily_sigma)
    for i in range(1, n):
        vol[i] = np.sqrt(
            0.00001 + 0.08 * returns[i - 1] ** 2 + 0.90 * vol[i - 1] ** 2
        )
        returns[i] = daily_mu + vol[i] * np.random.standard_normal()

    price = 44.4 * np.exp(np.cumsum(returns))
    # Generate OHLC from close
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
    print(f"Generated {len(df)} rows of synthetic GLD data ({start} to {end}).")
    return df


def load_gld_data() -> pd.DataFrame:
    """Try to fetch real data; fall back to synthetic if network is unavailable."""
    try:
        return fetch_gld_data()
    except Exception as e:
        print(f"Live fetch failed ({e}). Using synthetic data as fallback.")
        return generate_synthetic_gld()


if __name__ == "__main__":
    df = load_gld_data()
    print(df.head(10))
    print(f"\nDate range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"Shape: {df.shape}")
    df.to_csv("gld_data.csv", index=False)
    print("Saved to gld_data.csv")
