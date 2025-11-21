# confluence.py
"""
Reliable Confluence Generator for Render
- Forces yfinance to return valid data using start= instead of period=
- Uses /tmp cache for safe Render deployment
- Includes EMA trend + BOS detection
"""

import os
import logging
import pandas as pd
import numpy as np
import yfinance as yf

# -------- FIX 1: FORCE USER-AGENT (prevents empty DF from Yahoo) --------
yf.shared._default_user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

# -------- FIX 2: SAFE CACHE DIR FOR RENDER --------
os.environ["YFINANCE_CACHE_DIR"] = "/tmp/py-yfinance"
try:
    os.makedirs("/tmp/py-yfinance", exist_ok=True)
except Exception:
    pass

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("confluence")

# -------- PAIRS --------
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

# -------- TIMEFRAME SETTINGS (interval only) --------
TF_SETTINGS = {
    "Weekly": "1wk",
    "Daily": "1d",
    "H4": "4h",
    "H1": "1h",
}


# -------- FIX 3: RELIABLE DOWNLOAD FUNCTION --------
def safe_download(symbol, interval):
    """
    Uses start= instead of period= to bypass Yahoo restrictions.
    Always returns full data history so EMA can calculate properly.
    """

    try:
        df = yf.download(
            symbol,
            interval=interval,
            start="2018-01-01",
            progress=False,
            threads=False
        )

        if isinstance(df, pd.DataFrame) and not df.empty:
            return df

        log.warning("Empty DF for %s", symbol)
        return None

    except Exception as e:
        log.warning("safe_download failed for %s: %s", symbol, str(e))
        return None


# -------- EMA CALCULATION --------
def compute_ema(series, n):
    try:
        return series.ewm(span=n, adjust=False).mean()
    except Exception:
        return None


# -------- TREND LOGIC --------
def trend_from_ema(df, ema_period, strong_threshold=0.01):

    if df is None or "Close" not in df or df["Close"].empty:
        return None

    close = df["Close"].dropna()
    if len(close) < ema_period + 5:
        return None

    ema = compute_ema(close, ema_period)
    if ema is None or ema.empty:
        return None

    last_close = float(close.iloc[-1])
    last_ema = float(ema.iloc[-1])
    slope = last_ema - float(ema.iloc[-3]) if len(ema) > 3 else 0.0

    if last_close > last_ema * (1 + strong_threshold) and slope > 0:
        return "Strong Bullish"
    if last_close < last_ema * (1 - strong_threshold) and slope < 0:
        return "Strong Bearish"
    if last_close > last_ema:
        return "Bullish"
    if last_close < last_ema:
        return "Bearish"

    return "Neutral"


# -------- BOS DETECTION --------
def detect_bos(df):
    try:
        highs = df["High"].dropna()
        lows = df["Low"].dropna()

        bos = ""
        if len(highs) >= 3 and highs.iloc[-1] > highs.iloc[-2] > highs.iloc[-3]:
            bos = " (BOS_up)"
        if len(lows) >= 3 and lows.iloc[-1] < lows.iloc[-2] < lows.iloc[-3]:
            bos = " (BOS_down)"

        return bos

    except Exception:
        return ""


# -------- FINAL CONFLUENCE CALC --------
def get_confluence():

    results = []

    for item in PAIRS:
        symbol = item["Symbol"]
        name = item["Pair"]

        confluence = {"Weekly": "", "Daily": "", "H4": "", "H1": ""}

        for tf, interval in TF_SETTINGS.items():

            df = safe_download(symbol, interval)
            if df is None:
                continue

            # EMA settings
            ema_period = 200 if tf in ("Weekly", "Daily") else (50 if tf == "H4" else 20)

            trend = trend_from_ema(df, ema_period) or ""
            bos = detect_bos(df)

            confluence[tf] = trend + bos

        used = [v for v in confluence.values() if v]
        total = len(used)
        count = sum(1 for v in used if ("Bullish" in v or "Bearish" in v))

        percent = round((count / total) * 100) if total > 0 else 0

        results.append({
            "Pair": name,
            "Symbol": symbol,
            "Confluence": confluence,
            "ConfluencePercent": percent,
            "Summary": f"{percent}%" if percent > 0 else "No Confluence"
        })

    return results