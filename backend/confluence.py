"""
Produces JSON list of pairs with confluence per timeframe.
This implementation:
 - Ensures yfinance cache dir doesn't try to create /root/.cache issue by setting cache to /tmp
 - Tries to fetch appropriate intervals for weekly/daily/4h/1h
 - Computes simple EMA trend test vs 200-period (weekly/daily) and 50/20 for H4/H1 to decide Strong/Bullish/Bearish/Strong Bearish
 - If data unavailable, leaves blank and returns ConfluencePercent 0
"""
import os
os.environ["YFINANCE_NO_CACHE"] = "1"   # disable caching fully

import logging
import pandas as pd
import numpy as np
import yfinance as yf

# Patch yfinance cache location (Render allows /tmp only)
try:
    import yfinance.utils as yfutils
    _tmp_cache = "/tmp/py-yfinance"
    os.makedirs(_tmp_cache, exist_ok=True)
    yfutils._cache_dir = _tmp_cache
except Exception:
    pass

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("confluence")

# Master list - majors, minors, some exotics, indices and gold
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
    # exotics (examples)
    {"Pair": "USD/TRY", "Symbol": "USDTRY=X"},
    {"Pair": "USD/ZAR", "Symbol": "USDZAR=X"},
    {"Pair": "USD/MXN", "Symbol": "USDMXN=X"},
    # indices and metals
    {"Pair": "S&P 500", "Symbol": "^GSPC"},
    {"Pair": "Dow Jones", "Symbol": "^DJI"},
    {"Pair": "Nasdaq", "Symbol": "^IXIC"},
    {"Pair": "FTSE 100", "Symbol": "^FTSE"},
    {"Pair": "DAX", "Symbol": "^GDAXI"},
    {"Pair": "Gold", "Symbol": "GC=F"},
    {"Pair": "Silver", "Symbol": "SI=F"},
]

# timeframes mapping: timeframe -> (period to request, interval)
TF_SETTINGS = {
    "Weekly": ("3y", "1wk"),
    "Daily": ("1y", "1d"),
    "H4": ("60d", "4h"),
    "H1": ("7d", "1h"),
}

def safe_download(symbol, period, interval):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, threads=False)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df
        return None
    except Exception as e:
        log.warning("Failed to get ticker '%s' reason: %s", symbol, str(e))
        return None

def compute_ema(series, n):
    try:
        return series.ewm(span=n, adjust=False).mean()
    except Exception:
        return None

def trend_from_ema(df, ema_period, strong_threshold=0.01):
    # df expected to have 'Close'
    if df is None or 'Close' not in df or df['Close'].empty:
        return None
    close = df['Close'].dropna()
    if len(close) < ema_period // 2:
        return None
    ema = compute_ema(close, ema_period)
    if ema is None or ema.empty:
        return None
    last_close = float(close.iloc[-1])
    last_ema = float(ema.iloc[-1])
    # slope check (ema direction)
    slope = last_ema - float(ema.iloc[-3]) if len(ema) > 3 else last_ema - float(ema.iloc[0])
    if last_close > last_ema * (1 + strong_threshold) and slope > 0:
        return "Strong Bullish"
    if last_close > last_ema and slope >= 0:
        return "Bullish"
    if last_close < last_ema * (1 - strong_threshold) and slope < 0:
        return "Strong Bearish"
    if last_close < last_ema and slope <= 0:
        return "Bearish"
    return "Neutral"

def get_confluence():
    result = []
    for item in PAIRS:
        symbol = item["Symbol"]
        pair_name = item["Pair"]
        confluence = {"Weekly": "", "Daily": "", "H4": "", "H1": ""}
        # For weekly/daily use 200 EMA; for intraday shorter EMA
        try:
            for tf, (period, interval) in TF_SETTINGS.items():
                df = safe_download(symbol, period=period, interval=interval)
                if df is None:
                    confluence[tf] = ""
                    continue
                # choose ema length
                if tf in ("Weekly", "Daily"):
                    ema_period = 200
                elif tf == "H4":
                    ema_period = 50
                else:  # H1
                    ema_period = 20
                trend = trend_from_ema(df, ema_period)
                # simple Break of Structure (BOS) naive detection: compare last high/low to previous
                bos = ""
                try:
                    highs = df['High'].dropna()
                    lows = df['Low'].dropna()
                    if len(highs) >= 3:
                        if highs.iloc[-1] > highs.iloc[-2] and highs.iloc[-2] > highs.iloc[-3]:
                            bos = " (BOS_up)"
                        if lows.iloc[-1] < lows.iloc[-2] and lows.iloc[-2] < lows.iloc[-3]:
                            bos = " (BOS_down)"
                except Exception:
                    bos = ""
                confluence[tf] = (trend or "") + bos
        except Exception as e:
            log.exception("error building confluence for %s: %s", symbol, str(e))
        # compute percent: bullish-like or bearish-like count
        count = 0
        total = 0
        for v in confluence.values():
            if v:
                total += 1
                if "Bullish" in v or "Bearish" in v:
                    count += 1
        confluence_percent = round((count / (total or 1)) * 100) if total > 0 else 0
        summary = "No Confluence" if confluence_percent == 0 else f"{confluence_percent}%"
        result.append({
            "Pair": pair_name,
            "Symbol": symbol,
            "Confluence": confluence,
            "ConfluencePercent": confluence_percent,
            "Summary": summary
        })
    return result
