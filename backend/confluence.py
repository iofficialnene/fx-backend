"""
backend/confluence.py - Alpha Vantage API Version

Uses Alpha Vantage API with smart rate limiting for free tier:
- 25 API calls per day
- 5 calls per minute
- 30-minute cache to minimize API usage
"""

import os
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

import numpy as np
import pandas as pd

# Get API key from environment
ALPHAVANTAGE_API_KEY = os.environ.get("ALPHAVANTAGE_API_KEY", "")

# Logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("confluence")

# Forex pairs
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
]

# Timeframes - Alpha Vantage only supports daily, weekly, monthly
TF_SETTINGS = {
    "Weekly": {"function": "FX_WEEKLY", "interval": None},
    "Daily": {"function": "FX_DAILY", "interval": None},
}

# Cache - 30 minutes to save API calls
CACHE: Dict[Tuple[str, str], Tuple[float, Optional[pd.DataFrame]]] = {}
CACHE_TTL = 1800  # 30 minutes

# Rate limiting
LAST_REQUEST_TIME = 0
MIN_REQUEST_INTERVAL = 13  # 13 seconds between requests = ~4.6 per minute (safe for 5/min limit)

def _rate_limit():
    """Ensure we don't exceed 5 API calls per minute"""
    global LAST_REQUEST_TIME
    now = time.time()
    time_since_last = now - LAST_REQUEST_TIME
    if time_since_last < MIN_REQUEST_INTERVAL:
        sleep_time = MIN_REQUEST_INTERVAL - time_since_last
        log.info(f"Rate limiting: sleeping {sleep_time:.1f}s")
        time.sleep(sleep_time)
    LAST_REQUEST_TIME = time.time()

def _fetch_alphavantage(symbol: str, function: str) -> Optional[pd.DataFrame]:
    """Fetch data from Alpha Vantage API"""
    key = (symbol, function)
    now = time.time()
    
    # Check cache
    cached = CACHE.get(key)
    if cached:
        ts, df = cached
        if now - ts < CACHE_TTL:
            log.info(f"CACHE HIT {symbol} {function}")
            return df
    
    if not ALPHAVANTAGE_API_KEY:
        log.error("ALPHAVANTAGE_API_KEY not set!")
        return None
    
    try:
        # Rate limit
        _rate_limit()
        
        url = "https://www.alphavantage.co/query"
        params = {
            "function": function,
            "from_symbol": symbol[:3],
            "to_symbol": symbol[3:],
            "apikey": ALPHAVANTAGE_API_KEY,
            "outputsize": "full"
        }
        
        log.info(f"Fetching {symbol} {function}")
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            log.error(f"API error {response.status_code}")
            return None
        
        data = response.json()
        
        # Check for API limit message
        if "Note" in data:
            log.error(f"API limit hit: {data['Note']}")
            return None
        
        if "Error Message" in data:
            log.error(f"API error: {data['Error Message']}")
            return None
        
        # Get time series data
        if function == "FX_DAILY":
            time_series_key = "Time Series FX (Daily)"
        elif function == "FX_WEEKLY":
            time_series_key = "Time Series FX (Weekly)"
        else:
            log.error(f"Unknown function: {function}")
            return None
        
        if time_series_key not in data:
            log.error(f"No {time_series_key} in response")
            return None
        
        time_series = data[time_series_key]
        
        if not time_series:
            log.warning(f"Empty time series for {symbol} {function}")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame.from_dict(time_series, orient='index')
        
        if df.empty:
            return None
        
        # Convert index to datetime
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        
        # Rename columns
        df = df.rename(columns={
            '1. open': 'Open',
            '2. high': 'High',
            '3. low': 'Low',
            '4. close': 'Close'
        })
        
        # Convert to numeric
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Cache and return
        CACHE[key] = (now, df)
        log.info(f"Successfully fetched {len(df)} rows for {symbol} {function}")
        return df
        
    except Exception as e:
        log.exception(f"Error fetching {symbol} {function}: {e}")
        return None

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def _atr(df: pd.DataFrame, length: int = 14) -> Optional[pd.Series]:
    try:
        high = df["High"]
        low = df["Low"]
        close = df["Close"]
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=length, min_periods=1).mean()
        return atr
    except Exception:
        return None

def _detect_structure(df: pd.DataFrame, lookback: int = 10) -> str:
    try:
        if df is None or df.empty or len(df) < 6:
            return "UNKNOWN"
        
        highs = df["High"].dropna().tail(lookback)
        lows = df["Low"].dropna().tail(lookback)
        
        if len(highs) < 3 or len(lows) < 3:
            return "UNKNOWN"
        
        hi_idx = np.arange(len(highs))
        lo_idx = np.arange(len(lows))
        hi_slope = np.polyfit(hi_idx, highs.values, 1)[0]
        lo_slope = np.polyfit(lo_idx, lows.values, 1)[0]
        
        if hi_slope > 0 and lo_slope > 0:
            return "HH_HL"
        if hi_slope < 0 and lo_slope < 0:
            return "LH_LL"
        
        return "RANGE"
    except Exception:
        return "UNKNOWN"

def _detect_bos(df: pd.DataFrame) -> str:
    try:
        if df is None or df.empty or len(df) < 6:
            return ""
        
        highs = df["High"].dropna()
        lows = df["Low"].dropna()
        h_vals = highs.values
        l_vals = lows.values
        
        local_maxima = []
        for i in range(1, min(len(h_vals)-1, 200)):
            if h_vals[i] > h_vals[i-1] and h_vals[i] > h_vals[i+1]:
                local_maxima.append((i, h_vals[i]))
        
        local_minima = []
        for i in range(1, min(len(l_vals)-1, 200)):
            if l_vals[i] < l_vals[i-1] and l_vals[i] < l_vals[i+1]:
                local_minima.append((i, l_vals[i]))
        
        if len(local_maxima) >= 2:
            _, prev_val = local_maxima[-2]
            k, last_val = local_maxima[-1]
            if last_val > prev_val and (len(h_vals) - k) <= 8:
                return " (BOS_up)"
        
        if len(local_minima) >= 2:
            _, prev_val = local_minima[-2]
            k, last_val = local_minima[-1]
            if last_val < prev_val and (len(l_vals) - k) <= 8:
                return " (BOS_down)"
        
        return ""
    except Exception:
        return ""

def _compose_label(trend_label: Optional[str], structure_label: str, bos_label: str) -> str:
    base = trend_label or "No Trend"
    struct = f" ({structure_label})" if structure_label and structure_label not in ["UNKNOWN", "RANGE"] else (f" ({structure_label})" if structure_label == "RANGE" else "")
    return base + struct + (bos_label or "")

def _is_strong(trend_pct: float, atr: Optional[float], price: Optional[float]) -> bool:
    try:
        if price is None or price == 0:
            return False
        base_thresh = 0.008
        if atr and atr > 0:
            rel_atr = atr / price
            if rel_atr < 0.002:
                base_thresh *= 0.8
            elif rel_atr > 0.02:
                base_thresh *= 1.25
        return abs(trend_pct) >= base_thresh
    except Exception:
        return False

def _analyze_tf(df: pd.DataFrame, tf: str) -> Dict[str, Any]:
    out = {
        "trend_label": None,
        "structure": "UNKNOWN",
        "bos": "",
        "atr": None,
        "price": None,
        "label": "No Data"
    }
    
    if df is None or df.empty:
        return out
    
    try:
        close = df["Close"].dropna()
        if close.empty:
            return out
        
        price = float(close.iloc[-1])
        out["price"] = price
        
        atr_ser = _atr(df, length=14)
        atr_val = float(atr_ser.iloc[-1]) if atr_ser is not None and not atr_ser.empty else None
        out["atr"] = atr_val
        
        # Use 200 EMA for both Weekly and Daily
        ema_period = 200
        
        ema_series = _ema(close, ema_period)
        if ema_series is None or ema_series.empty:
            return out
        ema_val = float(ema_series.iloc[-1])
        
        trend_pct = (price - ema_val) / (ema_val if ema_val != 0 else price)
        strong_flag = _is_strong(trend_pct, atr_val, price)
        
        if trend_pct > 0:
            lbl = "Bullish"
        elif trend_pct < 0:
            lbl = "Bearish"
        else:
            lbl = "Neutral"
        
        if strong_flag:
            trend_label = "Strong " + lbl if lbl != "Neutral" else "Neutral"
        else:
            trend_label = lbl
        
        structure = _detect_structure(df, lookback=12)
        bos = _detect_bos(df)
        label = _compose_label(trend_label, structure, bos)
        
        out.update({
            "trend_label": trend_label,
            "structure": structure,
            "bos": bos,
            "label": label
        })
        
        return out
        
    except Exception:
        log.exception("Error analyzing timeframe")
        return out

def _compute_for_symbol(symbol: str) -> Dict[str, Any]:
    try:
        dfs = {}
        
        # Fetch timeframes (only Daily and Weekly available)
        for tf, settings in TF_SETTINGS.items():
            df = _fetch_alphavantage(symbol, settings["function"])
            dfs[tf] = df
        
        results = {}
        details = {}
        
        # Analyze available timeframes
        for tf in TF_SETTINGS.keys():
            df = dfs.get(tf)
            analysis = _analyze_tf(df, tf)
            label = analysis.get("label") or "No Data"
            results[tf] = label
            details[tf] = analysis
        
        # Add placeholders for H4 and H1 (not available in Alpha Vantage free tier)
        results["H4"] = "Not Available"
        results["H1"] = "Not Available"
        details["H4"] = {"label": "Not Available"}
        details["H1"] = {"label": "Not Available"}
        
        # Calculate confluence from available timeframes only
        dir_flags = []
        for tf in ["Weekly", "Daily"]:  # Only use these for confluence
            d = details.get(tf, {})
            tl = (d.get("trend_label") or "").lower()
            if "bull" in tl:
                dir_flags.append("bull")
            elif "bear" in tl:
                dir_flags.append("bear")
            else:
                dir_flags.append("neutral")
        
        bulls = sum(1 for x in dir_flags if x == "bull")
        bears = sum(1 for x in dir_flags if x == "bear")
        neutrals = sum(1 for x in dir_flags if x == "neutral")
        total = len(dir_flags) if dir_flags else 1
        
        if bulls > bears and bulls > neutrals:
            percent = round((bulls / total) * 100)
        elif bears > bulls and bears > neutrals:
            percent = round((bears / total) * 100)
        else:
            percent = round((max(bulls, bears, neutrals) / total) * 100)
        
        summary = f"{percent}% confluence" if percent > 0 else "No Confluence"
        
        return {
            "Symbol": symbol,
            "Confluence": results,
            "ConfluencePercent": int(percent),
            "Summary": summary,
            "Details": details
        }
        
    except Exception:
        log.exception(f"Error computing {symbol}")
        return {
            "Symbol": symbol,
            "Confluence": {tf: "No Data" for tf in ["Weekly", "Daily", "H4", "H1"]},
            "ConfluencePercent": 0,
            "Summary": "No Confluence",
            "Details": {}
        }

def get_confluence() -> List[Dict[str, Any]]:
    log.info("Starting confluence fetch - this will take ~3-4 minutes due to rate limiting")
    out = []
    for p in PAIRS:
        sym = p["Symbol"]
        pair_label = p["Pair"]
        log.info(f"Starting confluence for {pair_label} ({sym})")
        res = _compute_for_symbol(sym)
        res["Pair"] = pair_label
        out.append(res)
    log.info(f"Completed fetching {len(out)} pairs")
    return out