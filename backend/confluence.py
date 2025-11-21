"""
Fully fixed version of your original confluence generator.
- Preserves your logic & features
- Fixes percent always returning 0%
- Fixes empty trend strings
- Fixes None values breaking output
- Adds stronger trend detection
"""

import os
os.environ.setdefault("YFINANCE_CACHE_DIR", "/tmp/py-yfinance")
try:
    os.makedirs("/tmp/py-yfinance", exist_ok=True)
except:
    pass

import logging
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("confluence")

# ---------------------------------------
# PAIRS (your original list preserved)
# ---------------------------------------
PAIRS = [
    {"Pair": "EUR/USD", "Symbol": "EURUSD"},
    {"Pair": "GBP/USD", "Symbol": "GBPUSD"},
    {"Pair": "USD/JPY", "Symbol": "USDJPY"},
    {"Pair": "USD/CHF", "Symbol": "USDCHF"},
    {"Pair": "AUD/USD", "Symbol": "AUDUSD"},
    {"Pair": "NZD/USD", "Symbol": "NZDUSD"},
    {"Pair": "USD/CAD", "Symbol": "USDCAD"},
    {"Pair": "EUR/GBP", "Symbol": "EURGBP"},
    {"Pair": "EUR/JPY", "Symbol": "EURJPY"},
    {"Pair": "GBP/JPY", "Symbol": "GBPJPY"},
    {"Pair": "AUD/JPY", "Symbol": "AUDJPY"},
    {"Pair": "AUD/NZD", "Symbol": "AUDNZD"},
    {"Pair": "CHF/JPY", "Symbol": "CHFJPY"},
    {"Pair": "USD/TRY", "Symbol": "USDTRY"},
    {"Pair": "USD/ZAR", "Symbol": "USDZAR"},
    {"Pair": "USD/MXN", "Symbol": "USDMXN"},
    {"Pair": "S&P 500", "Symbol": "^GSPC"},
    {"Pair": "Dow Jones", "Symbol": "^DJI"},
    {"Pair": "Nasdaq", "Symbol": "^IXIC"},
    {"Pair": "FTSE 100", "Symbol": "^FTSE"},
    {"Pair": "DAX", "Symbol": "^GDAXI"},
    {"Pair": "Gold", "Symbol": "GC=F"},
    {"Pair": "Silver", "Symbol": "SI=F"},
]

TFS = ["Weekly", "Daily", "H4", "H1"]

# ---------------------------------------
# SAFE DOWNLOAD (same as original)
# ---------------------------------------
def safe_download(symbol, interval, start=None):
    try:
        df = yf.download(
            symbol,
            interval=interval,
            start=start,
            progress=False,
            threads=False,
            timeout=20,
        )
        if df is None or df.empty:
            return None

        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        if "Close" not in df.columns:
            if "Adj Close" in df.columns:
                df["Close"] = df["Adj Close"]
            else:
                return None

        return df
    except:
        return None


# ---------------------------------------
# EMA Trend Detection (improved)
# ---------------------------------------
def trend_from_ema(df, period):
    try:
        if df is None or df.empty:
            return ""

        close = df["Close"].dropna()
        if len(close) < period:
            return ""

        ema = close.ewm(span=period, adjust=False).mean()
        price = close.iloc[-1]
        ema_val = ema.iloc[-1]

        dist = (price - ema_val) / ema_val

        if dist > 0.015:
            return "Strong Bullish"
        if dist > 0:
            return "Bullish"
        if dist < -0.015:
            return "Strong Bearish"
        if dist < 0:
            return "Bearish"
        return "Neutral"
    except:
        return ""


# ---------------------------------------
# BOS detection (unchanged)
# ---------------------------------------
def detect_bos(df):
    try:
        highs = df["High"].dropna()
        lows = df["Low"].dropna()

        if len(highs) > 3 and highs.iloc[-1] > highs.iloc[-2] > highs.iloc[-3]:
            return " (BOS_up)"

        if len(lows) > 3 and lows.iloc[-1] < lows.iloc[-2] < lows.iloc[-3]:
            return " (BOS_down)"
    except:
        pass

    return ""


# ---------------------------------------
# FIXED: Confluence calculation
# ---------------------------------------
def get_confluence():
    output = []

    today = datetime.utcnow().date()
    start_daily = (today - timedelta(days=365)).isoformat()

    for item in PAIRS:
        sym = item["Symbol"]
        name = item["Pair"]

        # download base data
        daily = safe_download(sym, "1d", start=start_daily)
        h4 = safe_download(sym, "4h")
        h1 = safe_download(sym, "1h")
        weekly = safe_download(sym, "1wk")

        # fallback resampling if intraday missing
        if daily is not None:
            if h4 is None:
                h4 = daily.resample("4H").ffill()
            if h1 is None:
                h1 = daily.resample("1H").ffill()
            if weekly is None:
                weekly = daily.resample("W").agg(
                    {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
                )

        conf = {}

        # compute trends
        conf["Weekly"] = (trend_from_ema(weekly, 200) or "") + detect_bos(weekly)
        conf["Daily"] = (trend_from_ema(daily, 200) or "") + detect_bos(daily)
        conf["H4"] = (trend_from_ema(h4, 50) or "") + detect_bos(h4)
        conf["H1"] = (trend_from_ema(h1, 20) or "") + detect_bos(h1)

        # ---------------------------------------
        # FIXED: Confluence % calculation
        # ---------------------------------------
        valid = [v for v in conf.values() if v.strip() != ""]
        score = 0

        for v in valid:
            if "Strong Bullish" in v or "Strong Bearish" in v:
                score += 3
            elif "Bullish" in v or "Bearish" in v:
                score += 2
            elif "Neutral" in v:
                score += 1

        max_score = 3 * len(valid)
        percent = round((score / max_score) * 100) if max_score > 0 else 0

        output.append({
            "Pair": name,
            "Symbol": sym,
            "Confluence": conf,
            "ConfluencePercent": percent,
            "Summary": f"{percent}%",
        })

    return output