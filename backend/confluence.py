# backend/confluence.py
"""
Confluence generator - robust, Render-safe.
- Forces yfinance cache into /tmp
- Uses proper '=X' currency tickers (Yahoo expects these)
- Safe download with retries and MultiIndex fixes
- EMA trend detection (200 / 50 / 20)
- Fallbacks: resample daily into intraday if intraday blocked
- Returns list of dicts used by frontend
"""

import os
# MUST set before importing yfinance
os.environ.setdefault("YFINANCE_CACHE_DIR", "/tmp/py-yfinance")
os.environ.setdefault("YFINANCE_NO_CACHE", "1")

try:
    os.makedirs("/tmp/py-yfinance", exist_ok=True)
except Exception:
    pass

import logging
import time
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import yfinance as yf

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("confluence")

# ---------------------------
# PAIRS: currency tickers use =X (Yahoo format)
# ---------------------------
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

# simple timeframe names front expects
TF_SETTINGS = {
    "Weekly": {"interval": "1wk", "lookback_days": 365*3},
    "Daily": {"interval": "1d", "lookback_days": 365},
    "H4": {"interval": "4h", "lookback_days": 60},
    "H1": {"interval": "1h", "lookback_days": 7},
}

# ---------------------------
# safe_download: retries + multi-index fix
# ---------------------------
def safe_download(symbol, interval, start=None, end=None, retries=2, pause=1):
    kwargs = dict(tickers=symbol, interval=interval, progress=False, threads=False, timeout=20)
    if start:
        kwargs["start"] = start
    if end:
        kwargs["end"] = end

    for attempt in range(retries + 1):
        try:
            df = yf.download(**kwargs)
            # If MultiIndex columns (sometimes happens) -> flatten
            if isinstance(getattr(df, "columns", None), pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if df is None or df.empty:
                log.debug("safe_download empty for %s @%s (attempt %s)", symbol, interval, attempt)
                df = None
            else:
                # ensure datetime index & sorted
                try:
                    df.index = pd.to_datetime(df.index)
                except Exception:
                    pass
                df = df.sort_index()
                # ensure Close column exists (map Adjusted -> Close if needed)
                if "Close" not in df.columns and "Adj Close" in df.columns:
                    df["Close"] = df["Adj Close"]
                if "Close" not in df.columns:
                    log.debug("safe_download: no Close col for %s @%s", symbol, interval)
                    df = None

            if df is not None:
                return df
        except Exception as e:
            log.warning("safe_download failed for %s @%s attempt %s: %s", symbol, interval, attempt, e)
        if attempt < retries:
            time.sleep(pause)
    return None

# ---------------------------
# resample daily -> intraday fallback
# ---------------------------
def resample_from_daily(df_daily, rule="4H"):
    try:
        if df_daily is None or df_daily.empty:
            return None
        start = df_daily.index.min()
        end = df_daily.index.max() + pd.Timedelta(days=1)
        rng = pd.date_range(start=start, end=end, freq=rule, closed="left")
        o = df_daily["Open"].reindex(rng, method="ffill")
        h = df_daily["High"].reindex(rng, method="ffill")
        l = df_daily["Low"].reindex(rng, method="ffill")
        c = df_daily["Close"].reindex(rng, method="ffill")
        vol = df_daily["Volume"].reindex(rng, method="ffill").fillna(0)
        new = pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c, "Volume": vol}, index=rng)
        return new
    except Exception:
        return None

# ---------------------------
# EMA & trend
# ---------------------------
def compute_ema(series, n):
    try:
        return series.ewm(span=n, adjust=False).mean()
    except Exception:
        return None

def trend_from_ema(df, ema_period, strong_threshold=0.01):
    try:
        if df is None or df.empty or "Close" not in df:
            return None
        close = df["Close"].dropna()
        if len(close) < max(10, ema_period // 2):
            return None
        ema = compute_ema(close, ema_period)
        if ema is None or ema.empty:
            return None
        last_close = float(close.iloc[-1])
        last_ema = float(ema.iloc[-1])
        slope = (float(ema.iloc[-1]) - float(ema.iloc[-3])) if len(ema) > 3 else 0.0
        if last_close > last_ema * (1 + strong_threshold) and slope > 0:
            return "Strong Bullish"
        if last_close > last_ema and slope >= 0:
            return "Bullish"
        if last_close < last_ema * (1 - strong_threshold) and slope < 0:
            return "Strong Bearish"
        if last_close < last_ema and slope <= 0:
            return "Bearish"
        return "Neutral"
    except Exception:
        return None

# ---------------------------
# BOS detection
# ---------------------------
def detect_bos(df):
    try:
        highs = df["High"].dropna()
        lows = df["Low"].dropna()
        if len(highs) >= 3 and highs.iloc[-1] > highs.iloc[-2] > highs.iloc[-3]:
            return " (BOS_up)"
        if len(lows) >= 3 and lows.iloc[-1] < lows.iloc[-2] < lows.iloc[-3]:
            return " (BOS_down)"
    except Exception:
        pass
    return ""

# ---------------------------
# Main: get_confluence
# ---------------------------
def get_confluence():
    result = []
    today = datetime.utcnow().date()
    for pair in PAIRS:
        symbol = pair["Symbol"]
        pair_name = pair["Pair"]
        confluence = {tf: "" for tf in TF_SETTINGS.keys()}

        # Attempt daily + weekly first (stable)
        try:
            daily_start = (today - timedelta(days=TF_SETTINGS["Daily"]["lookback_days"])).isoformat()
            weekly_start = (today - timedelta(days=TF_SETTINGS["Weekly"]["lookback_days"])).isoformat()
        except Exception:
            daily_start = None
            weekly_start = None

        daily_df = safe_download(symbol, TF_SETTINGS["Daily"]["interval"], start=daily_start)
        weekly_df = safe_download(symbol, TF_SETTINGS["Weekly"]["interval"], start=weekly_start)

        # try intraday; if fails resample from daily
        h4_df = safe_download(symbol, TF_SETTINGS["H4"]["interval"])
        h1_df = safe_download(symbol, TF_SETTINGS["H1"]["interval"])

        if h4_df is None and daily_df is not None:
            h4_df = resample_from_daily(daily_df, "4H")
        if h1_df is None and daily_df is not None:
            h1_df = resample_from_daily(daily_df, "1H")

        # resample weekly if missing and daily present
        if weekly_df is None and daily_df is not None:
            try:
                weekly_df = daily_df.resample("W").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"})
            except Exception:
                weekly_df = None

        # compute trends
        try:
            if weekly_df is not None:
                t = trend_from_ema(weekly_df, 200)
                confluence["Weekly"] = (t or "") + detect_bos(weekly_df)
            if daily_df is not None:
                t = trend_from_ema(daily_df, 200)
                confluence["Daily"] = (t or "") + detect_bos(daily_df)
            if h4_df is not None:
                t = trend_from_ema(h4_df, 50)
                fallback = "" if safe_download(symbol, TF_SETTINGS["H4"]["interval"]) is not None else " (no_intraday)"
                confluence["H4"] = (t or "") + detect_bos(h4_df) + fallback
            if h1_df is not None:
                t = trend_from_ema(h1_df, 20)
                fallback = "" if safe_download(symbol, TF_SETTINGS["H1"]["interval"]) is not None else " (no_intraday)"
                confluence["H1"] = (t or "") + detect_bos(h1_df) + fallback
        except Exception as e:
            log.exception("trend compute error for %s: %s", symbol, e)

        used = [v for v in confluence.values() if v and v.strip()]
        total = len(used)
        count = sum(1 for v in used if ("Bullish" in v or "Bearish" in v))
        percent = round((count / total) * 100) if total > 0 else 0

        result.append({
            "Pair": pair_name,
            "Symbol": symbol,
            "Confluence": confluence,
            "ConfluencePercent": percent,
            "Summary": f"{percent}%" if percent > 0 else "No Confluence"
        })

    return result
