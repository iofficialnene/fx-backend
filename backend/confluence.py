# confluence.py
"""
Confluence generator — Render/Heroku-safe backend.
- Forces yfinance cache into /tmp to avoid /root/.cache creation errors
- Uses stable currency tickers (no "=X")
- Attempts intraday download, falls back gracefully if blocked
- Resamples where appropriate
- EMA trend detection + naive BOS detection
"""

import os
# force yfinance to use /tmp (safe on most PaaS)
os.environ.setdefault("YFINANCE_CACHE_DIR", "/tmp/py-yfinance")
try:
    os.makedirs("/tmp/py-yfinance", exist_ok=True)
except Exception:
    pass

import logging
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("confluence")

# --------------------------
# Master pair list (stable tickers)
# Remove '=X' on currency tickers to avoid Render/Yahoo issues
# Keep ^ for indices and GC=F / SI=F for metals
# --------------------------
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

# Timeframes we want to show
TFS = ["Weekly", "Daily", "H4", "H1"]

# For yfinance calls: prefer daily as stable. We'll attempt intraday and fallback if needed.
YF_DAILY_INTERVAL = "1d"
YF_WEEKLY_INTERVAL = "1wk"
YF_4H_INTERVAL = "4h"
YF_1H_INTERVAL = "1h"

# Data window defaults
DEFAULT_DAYS_FOR_DAILY = 365  # 1 year approx
DEFAULT_DAYS_FOR_WEEKLY = 365 * 3  # 3 years to get weekly smoothing

# --------------------------
# helper: safe download with timeouts + MultiIndex fix
# --------------------------
def safe_download(symbol: str, interval: str, start: str = None, end: str = None):
    """
    Try to download data from yfinance. If empty or error, return None.
    Avoids throwing exceptions up the stack.
    """
    try:
        kwargs = dict(tickers=symbol, interval=interval, progress=False, threads=False, timeout=25)
        if start:
            kwargs["start"] = start
        if end:
            kwargs["end"] = end

        df = yf.download(**kwargs)

        # Some yfinance versions return MultiIndex columns (if you pass multiple tickers)
        if isinstance(getattr(df, "columns", None), pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df is None or df.empty:
            log.debug("safe_download: empty DataFrame for %s @%s", symbol, interval)
            return None

        # ensure datetime index and sorted
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            pass
        df = df.sort_index()

        # normalize column names if lowercase or mixed
        cols = {c: c for c in df.columns}
        # ensure expected columns exist
        if "Close" not in df.columns:
            # sometimes 'Adj Close' exists — try to map
            if "Adj Close" in df.columns:
                df["Close"] = df["Adj Close"]
            else:
                log.debug("safe_download: no Close column for %s @%s", symbol, interval)
                return None

        return df
    except Exception as e:
        log.warning("safe_download failed for %s @%s : %s", symbol, interval, e, exc_info=False)
        return None

# --------------------------
# resample intraday from daily fallback (if intraday blocked)
# --------------------------
def resample_from_daily(df_daily: pd.DataFrame, rule: str):
    """
    When intraday data can't be fetched, approximate intraday by forward-filling daily values.
    This is a fallback: not ideal for real intraday, but avoids empties.
    rule example: '4H' or '1H'
    """
    try:
        # create hourly index for last N days
        start = df_daily.index.min()
        end = df_daily.index.max() + pd.Timedelta(days=1)

        rng = pd.date_range(start=start, end=end, freq=rule, closed="left", tz=None)
        # Use last available close for the timestamp (forward-fill on a reindexed series)
        o = df_daily["Open"].reindex(rng, method="ffill")
        h = df_daily["High"].reindex(rng, method="ffill")
        l = df_daily["Low"].reindex(rng, method="ffill")
        c = df_daily["Close"].reindex(rng, method="ffill")
        vol = df_daily["Volume"].reindex(rng, method="ffill").fillna(0)

        df = pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c, "Volume": vol}, index=rng)
        return df
    except Exception:
        return None

# --------------------------
# EMA helpers & trend detection
# --------------------------
def compute_ema(series: pd.Series, n: int):
    try:
        return series.ewm(span=n, adjust=False).mean()
    except Exception:
        return None

def trend_from_ema(df: pd.DataFrame, ema_period: int, strong_threshold: float = 0.01):
    """
    Returns: "Strong Bullish" / "Bullish" / "Neutral" / "Bearish" / "Strong Bearish" or None
    """
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
        slope = float(ema.iloc[-1] - ema.iloc[-3]) if len(ema) > 3 else 0.0

        if last_close > last_ema * (1 + strong_threshold) and slope > 0:
            return "Strong Bullish"
        if last_close < last_ema * (1 - strong_threshold) and slope < 0:
            return "Strong Bearish"
        if last_close > last_ema and slope >= 0:
            return "Bullish"
        if last_close < last_ema and slope <= 0:
            return "Bearish"
        return "Neutral"
    except Exception:
        return None

# --------------------------
# naive BOS detection
# --------------------------
def detect_bos(df: pd.DataFrame):
    """
    Very naive: if the last 3 highs increase -> BOS_up
                 if the last 3 lows decrease -> BOS_down
    """
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

# --------------------------
# Primary function used by API
# --------------------------
def get_confluence():
    """
    Returns a list of dicts:
    [
      {
        "Pair": "EUR/USD",
        "Symbol": "EURUSD",
        "Confluence": {"Weekly": "...", "Daily": "...", "H4": "...", "H1": "..."},
        "ConfluencePercent": 50,
        "Summary": "50%"
      }, ...
    ]
    """
    output = []

    # time windows / periods
    today = datetime.utcnow().date()
    daily_start = (today - timedelta(days=DEFAULT_DAYS_FOR_DAILY)).isoformat()
    weekly_start = (today - timedelta(days=DEFAULT_DAYS_FOR_WEEKLY)).isoformat()

    for item in PAIRS:
        symbol = item["Symbol"]
        pair_name = item["Pair"]

        confluence = {tf: "" for tf in TFS}

        # 1) fetch daily (stable)
        daily_df = safe_download(symbol, YF_DAILY_INTERVAL, start=daily_start)
        # 2) fetch weekly (optional) - try weekly download for proper weekly candles
        weekly_df = safe_download(symbol, YF_WEEKLY_INTERVAL, start=weekly_start)
        # 3) try intraday (H4/H1) directly; if fails, fallback to resampled daily
        h4_df = safe_download(symbol, YF_4H_INTERVAL)
        h1_df = safe_download(symbol, YF_1H_INTERVAL)

        # If intraday is None, attempt fallback using daily resample (approximate, not real intraday)
        if h4_df is None and daily_df is not None:
            h4_df = resample_from_daily(daily_df, "4H")
        if h1_df is None and daily_df is not None:
            h1_df = resample_from_daily(daily_df, "1H")

        # if weekly_df None but daily available, resample daily->weekly
        if weekly_df is None and daily_df is not None:
            try:
                weekly_df = daily_df.resample("W").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
            except Exception:
                weekly_df = None

        # compute each timeframe trend + bos if present
        try:
            # Weekly
            if weekly_df is not None:
                trend = trend_from_ema(weekly_df, 200)
                bos = detect_bos(weekly_df)
                confluence["Weekly"] = (trend or "") + bos

            # Daily
            if daily_df is not None:
                trend = trend_from_ema(daily_df, 200)
                bos = detect_bos(daily_df)
                confluence["Daily"] = (trend or "") + bos

            # H4
            if h4_df is not None:
                trend = trend_from_ema(h4_df, 50)
                bos = detect_bos(h4_df)
                # mark if this is a fallback from daily resample
                fallback_flag = "" if safe_download(symbol, YF_4H_INTERVAL) is not None else " (no_intraday)"
                confluence["H4"] = (trend or "") + bos + fallback_flag

            # H1
            if h1_df is not None:
                trend = trend_from_ema(h1_df, 20)
                bos = detect_bos(h1_df)
                fallback_flag = "" if safe_download(symbol, YF_1H_INTERVAL) is not None else " (no_intraday)"
                confluence["H1"] = (trend or "") + bos + fallback_flag

        except Exception as e:
            log.exception("error computing confluence for %s: %s", symbol, e)

        # calculate ConfluencePercent: percent of non-empty TFs that are Bullish/Bearish
        used = [v for v in confluence.values() if v]
        total = len(used)
        count = sum(1 for v in used if ("Bullish" in v or "Bearish" in v))
        percent = round((count / total) * 100) if total > 0 else 0

        output.append({
            "Pair": pair_name,
            "Symbol": symbol,
            "Confluence": confluence,
            "ConfluencePercent": percent,
            "Summary": f"{percent}%" if percent > 0 else "No Confluence"
        })

    return output