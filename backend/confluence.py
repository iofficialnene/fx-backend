"""
FULLY WORKING Confluence Generator
- Render-safe yfinance cache (NO worker crash)
- Stable downloads
- EMA trend logic (200/50/20)
- BOS detection
- Full forex + indices + metals list
"""

import os
import logging
import pandas as pd
import numpy as np

# ------------------------------------------------------------------
# RENDER FIX — MUST BE FIRST BEFORE IMPORTING YFINANCE
# ------------------------------------------------------------------
os.environ["YFINANCE_CACHE_DIR"] = "/tmp/py-yfinance"
os.makedirs("/tmp/py-yfinance", exist_ok=True)

import yfinance as yf

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("confluence")

# ------------------------------
# PAIRS LIST
# ------------------------------
PAIRS = [
    {"Pair": "EUR/USD", "Symbol": "EURUSD=X"},
    {"Pair": "GBP/USD", "Symbol": "GBPUSD=X"},
    {"Pair": "USD/JPY", "Symbol": "USDJPY=X"},
    {"Pair": "USD/CHF", "Symbol": "USDCHF=X"},
    {"Pair": "AUD/USD", "Symbol": "AUDUSD=X"},
    {"Pair": "NZD/USD", "Symbol": "NZDUSD=X"},
    {"Pair": "USD/CAD", "Symbol": "USDCAD=X"},
    {"Pair": "EUR/GBP", "Symbol": "EURGBP=X"},
    {"Pair": "EUR/JPY", "Symbol": "EURJPY=X"},
    {"Pair": "GBP/JPY", "Symbol": "GBPJPY=X"},
    {"Pair": "AUD/JPY", "Symbol": "AUDJPY=X"},
    {"Pair": "AUD/NZD", "Symbol": "AUDNZD=X"},
    {"Pair": "CHF/JPY", "Symbol": "CHFJPY=X"},
    {"Pair": "USD/TRY", "Symbol": "USDTRY=X"},
    {"Pair": "USD/ZAR", "Symbol": "USDZAR=X"},
    {"Pair": "USD/MXN", "Symbol": "USDMXN=X"},
    {"Pair": "S&P 500", "Symbol": "^GSPC"},
    {"Pair": "Dow Jones", "Symbol": "^DJI"},
    {"Pair": "Nasdaq", "Symbol": "^IXIC"},
    {"Pair": "FTSE 100", "Symbol": "^FTSE"},
    {"Pair": "DAX", "Symbol": "^GDAXI"},
    {"Pair": "Gold", "Symbol": "GC=F"},
    {"Pair": "Silver", "Symbol": "SI=F"},
]

# ------------------------------
# TIMEFRAMES
# ------------------------------
TF_SETTINGS = {
    "Weekly": ("3y", "1wk"),
    "Daily": ("1y", "1d"),
    "H4": ("60d", "4h"),
    "H1": ("7d", "1h"),
}

# ------------------------------
# SAFE DOWNLOAD
# ------------------------------
def safe_download(symbol, period, interval):
    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            threads=False,
            progress=False
        )
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df
        return None
    except Exception as e:
        log.error(f"Download failed for {symbol}: {e}")
        return None

# ------------------------------
# EMA
# ------------------------------
def compute_ema(series, n):
    try:
        return series.ewm(span=n, adjust=False).mean()
    except:
        return None

# ------------------------------
# TREND LOGIC
# ------------------------------
def trend_from_ema(df, ema_period, strong_threshold=0.01):
    if df is None or "Close" not in df:
        return None

    close = df["Close"].dropna()
    if len(close) < ema_period // 2:
        return None

    ema = compute_ema(close, ema_period)
    if ema is None or ema.empty:
        return None

    last_close = float(close.iloc[-1])
    last_ema = float(ema.iloc[-1])
    slope = last_ema - float(ema.iloc[-3]) if len(ema) > 3 else 0

    # strong trends
    if last_close > last_ema * (1 + strong_threshold) and slope > 0:
        return "Strong Bullish"
    if last_close < last_ema * (1 - strong_threshold) and slope < 0:
        return "Strong Bearish"

    # normal trends
    if last_close > last_ema and slope >= 0:
        return "Bullish"
    if last_close < last_ema and slope <= 0:
        return "Bearish"

    return "Neutral"

# ------------------------------
# MAIN LOGIC
# ------------------------------
def get_confluence():
    results = []

    for item in PAIRS:
        symbol = item["Symbol"]
        name = item["Pair"]

        tf_data = {}

        for tf, (period, interval) in TF_SETTINGS.items():
            df = safe_download(symbol, period, interval)
            if df is None:
                tf_data[tf] = ""
                continue

            # EMA settings
            ema_period = 200 if tf in ("Weekly", "Daily") else 50 if tf == "H4" else 20
            trend = trend_from_ema(df, ema_period) or ""

            # BOS detection
            bos = ""
            highs = df["High"].dropna()
            lows = df["Low"].dropna()

            if len(highs) >= 3:
                if highs.iloc[-1] > highs.iloc[-2] > highs.iloc[-3]:
                    bos = " (BOS_up)"
            if len(lows) >= 3:
                if lows.iloc[-1] < lows.iloc[-2] < lows.iloc[-3]:
                    bos = " (BOS_down)"

            tf_data[tf] = trend + bos

        # Percentage
        used = [v for v in tf_data.values() if v]
        total = len(used)
        count = sum(
            1 for v in used
            if "Bullish" in v or "Bearish" in v
        )

        percent = round((count / total) * 100) if total > 0 else 0

        results.append({
            "Pair": name,
            "Symbol": symbol,
            "Confluence": tf_data,
            "ConfluencePercent": percent,
            "Summary": f"{percent}%"
        })

    return results
