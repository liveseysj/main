#!/usr/bin/env python3
"""
Scalp Dashboard Server
======================
Real-time trade monitoring dashboard for finding stocks with wide spreads
and high trade frequency.  Uses Polygon.io WebSocket for live market data.

Usage:
    export POLYGON_API_KEY=your_key
    python dashboard/server.py              # live mode
    python dashboard/server.py --demo       # fake data for testing
    python dashboard/server.py --port 9000  # custom port
"""

import argparse
import asyncio
import csv
import json
import math
import os
import random
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import websockets
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "")
POLYGON_WS_URL = "wss://socket.polygon.io/stocks"
SYMBOLS_CSV = Path(__file__).resolve().parent.parent / "scalp_symbols.csv"
MAX_BUFFER_MIN = 60          # keep up to 60 min of trades per ticker
UPDATE_INTERVAL_SEC = 1.0    # push metrics to frontend every N seconds

# ---------------------------------------------------------------------------
# Global mutable state (single-user dashboard, single process)
# ---------------------------------------------------------------------------

# Per-ticker trade buffer: deque of (timestamp_ms, price, size)
trade_buffers: dict[str, deque] = defaultdict(lambda: deque(maxlen=500_000))
tickers: list[str] = []
clients: list[WebSocket] = []
paused: bool = False
demo_mode: bool = False

# User-tuneable parameters (updated from frontend)
params: dict[str, float] = {
    "min_shares": 100,
    "count_window_sec": 60,
    "std_window_min": 5,
    "trend_window_min": 5,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_tickers() -> list[str]:
    """Read ticker symbols from scalp_symbols.csv."""
    path = SYMBOLS_CSV
    if not path.exists():
        print(f"[WARN] {path} not found — using empty ticker list")
        return []
    result: list[str] = []
    with open(path) as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return []
        # detect column index
        col = 0
        for i, h in enumerate(header):
            if h.strip().lower() in ("ticker", "symbol", "sym", "tickers", "symbols"):
                col = i
                break
        else:
            # no recognised header — first cell might already be a ticker
            val = header[0].strip()
            if val.isalpha() and 1 <= len(val) <= 5:
                result.append(val.upper())
        for row in reader:
            if row and row[col].strip():
                result.append(row[col].strip().upper())
    return sorted(set(result))


def compute_metrics(ticker: str) -> dict:
    """Compute all dashboard columns for one ticker."""
    buf = trade_buffers[ticker]
    now_ms = time.time() * 1000
    min_sz = params["min_shares"]

    last_price = buf[-1][1] if buf else None

    # size-filtered trades (materialise once)
    big = [(t, p, s) for t, p, s in buf if s >= min_sz]

    # ---- trade count in window ----
    count_cutoff = now_ms - params["count_window_sec"] * 1000
    trade_count = sum(1 for t, p, s in big if t >= count_cutoff)

    # ---- gap std dev ----
    std_cutoff = now_ms - params["std_window_min"] * 60_000
    std_prices = [p for t, p, s in big if t >= std_cutoff]

    gap_std_d = 0.0
    gap_std_p = 0.0
    n_gaps = 0
    if len(std_prices) >= 2:
        arr = np.array(std_prices)
        gaps = np.diff(arr)
        n_gaps = len(gaps)
        gap_std_d = float(np.std(gaps, ddof=0))
        pct_gaps = gaps / arr[:-1] * 100
        gap_std_p = float(np.std(pct_gaps, ddof=0))

    # ---- trend (linear-regression slope, $/min) ----
    trend_cutoff = now_ms - params["trend_window_min"] * 60_000
    trend_data = [(t, p) for t, p, s in big if t >= trend_cutoff]

    trend = 0.0
    if len(trend_data) >= 2:
        ts = np.array([t for t, p in trend_data])
        ps = np.array([p for t, p in trend_data])
        t_min = (ts - ts[0]) / 60_000  # elapsed minutes
        if t_min[-1] > 0:
            trend = float(np.polyfit(t_min, ps, 1)[0])

    # ---- ratio (std / |trend|) ----
    ratio = gap_std_d / abs(trend) if abs(trend) > 1e-8 else 9999.99
    ratio = min(ratio, 9999.99)

    return {
        "ticker": ticker,
        "last_price": round(last_price, 4) if last_price is not None else None,
        "trade_count": trade_count,
        "gap_std_dollar": round(gap_std_d, 4),
        "gap_std_pct": round(gap_std_p, 4),
        "trend": round(trend, 6),
        "ratio": round(ratio, 2),
        "n_gaps": n_gaps,
    }


# ---------------------------------------------------------------------------
# Polygon WebSocket listener
# ---------------------------------------------------------------------------

async def polygon_listener():
    """Connect to Polygon and ingest trade ticks forever."""
    if not POLYGON_API_KEY:
        print("[WARN] POLYGON_API_KEY not set — no live data")
        return

    while True:
        try:
            async with websockets.connect(POLYGON_WS_URL) as ws:
                msg = await ws.recv()
                print(f"[Polygon] {msg}")

                await ws.send(json.dumps({"action": "auth", "params": POLYGON_API_KEY}))
                msg = await ws.recv()
                print(f"[Polygon] Auth response: {msg}")

                # subscribe in batches of 100 to avoid message-size limits
                for i in range(0, len(tickers), 100):
                    batch = tickers[i:i + 100]
                    subs = ",".join(f"T.{t}" for t in batch)
                    await ws.send(json.dumps({"action": "subscribe", "params": subs}))
                    ack = await ws.recv()
                    print(f"[Polygon] Subscribed batch {i // 100 + 1}: {ack[:120]}")

                print(f"[Polygon] Listening for trades on {len(tickers)} tickers...")
                async for raw in ws:
                    if paused:
                        continue
                    data = json.loads(raw)
                    if not isinstance(data, list):
                        data = [data]
                    for item in data:
                        if item.get("ev") == "T":
                            sym = item.get("sym", "")
                            price = item.get("p")
                            size = item.get("s", 0)
                            ts = item.get("t", time.time() * 1000)
                            if sym and price is not None:
                                trade_buffers[sym].append((ts, float(price), int(size)))

        except Exception as e:
            print(f"[Polygon] Error: {e}. Reconnecting in 5 s...")
            await asyncio.sleep(5)


# ---------------------------------------------------------------------------
# Demo-mode fake-data generator
# ---------------------------------------------------------------------------

async def demo_generator():
    """Produce synthetic trades so the dashboard can be tested without an API key."""
    base_prices = {t: random.uniform(15, 600) for t in tickers}
    vols = {t: random.uniform(0.0001, 0.0008) for t in tickers}

    while True:
        if not paused:
            now_ms = time.time() * 1000
            for t in tickers:
                # ~1-8 trades per tick per ticker
                n = random.randint(1, 8)
                for _ in range(n):
                    base_prices[t] *= 1 + random.gauss(0, vols[t])
                    price = round(base_prices[t], 2)
                    size = random.choice([1, 5, 10, 25, 50, 100, 100, 200, 500, 1000])
                    trade_buffers[t].append((now_ms + random.uniform(-50, 50), price, size))
        await asyncio.sleep(0.1)


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------

async def prune_buffers():
    """Remove trades older than MAX_BUFFER_MIN from all buffers."""
    while True:
        await asyncio.sleep(30)
        cutoff = time.time() * 1000 - MAX_BUFFER_MIN * 60_000
        for buf in trade_buffers.values():
            while buf and buf[0][0] < cutoff:
                buf.popleft()


async def broadcast_updates():
    """Compute metrics and push them to every connected frontend client."""
    while True:
        await asyncio.sleep(UPDATE_INTERVAL_SEC)
        if not clients:
            continue
        rows = [compute_metrics(t) for t in tickers]
        payload = json.dumps({"type": "update", "rows": rows, "paused": paused})
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            clients.remove(ws)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tickers
    tickers = load_tickers()
    print(f"[Dashboard] Loaded {len(tickers)} tickers: {tickers[:20]}")

    tasks = [
        asyncio.create_task(prune_buffers()),
        asyncio.create_task(broadcast_updates()),
    ]
    if demo_mode:
        print("[Dashboard] Running in DEMO mode with synthetic trades")
        tasks.append(asyncio.create_task(demo_generator()))
    else:
        tasks.append(asyncio.create_task(polygon_listener()))

    yield

    for t in tasks:
        t.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent / "index.html", media_type="text/html")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    global paused
    await ws.accept()
    clients.append(ws)
    try:
        # send initial state so frontend can populate controls
        await ws.send_text(json.dumps({
            "type": "init",
            "tickers": tickers,
            "params": params,
            "paused": paused,
            "demo": demo_mode,
        }))
        while True:
            msg = json.loads(await ws.receive_text())
            if msg.get("type") == "params":
                for k, v in msg["params"].items():
                    if k in params:
                        params[k] = float(v)
            elif msg.get("type") == "pause":
                paused = bool(msg.get("paused", False))
    except WebSocketDisconnect:
        pass
    finally:
        if ws in clients:
            clients.remove(ws)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    global demo_mode
    parser = argparse.ArgumentParser(description="Scalp Dashboard Server")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--demo", action="store_true", help="Generate fake trade data for testing")
    args = parser.parse_args()

    demo_mode = args.demo
    if not POLYGON_API_KEY and not demo_mode:
        print("=" * 60)
        print("  No POLYGON_API_KEY found.  Run with --demo for fake data:")
        print("    python dashboard/server.py --demo")
        print("  Or set your key:")
        print("    export POLYGON_API_KEY=your_key_here")
        print("=" * 60)

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
