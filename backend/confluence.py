"""
backend/confluence.py - Twelve Data API Version

Uses Twelve Data API instead of Yahoo Finance for reliable cloud server access.
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
TWELVEDATA_API_KEY = os.environ.get("TWELVEDATA_API_KEY", "")

# Logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("confluence")

# Forex pairs mapping (Twelve Data format)
PAIRS = [
    {"Pair": "EUR/USD", "Symbol": "EUR/USD"},
    {"Pair": "GBP/USD", "Symbol": "GBP/USD"},
    {"Pair": "USD/JPY", "Symbol": "USD/JPY"},
    {"Pair": "USD/CHF", "Symbol": "USD/CHF"},
    {"Pair": "AUD/USD", "Symbol": "AUD/USD"},
    {"Pair": "NZD/USD", "Symbol": "NZD/USD"},
    {"Pair": "USD/CAD", "Symbol": "USD/CAD"},
    {"Pair": "EUR/GBP", "Symbol": "EUR/GBP"},
    {"Pair": "EUR/JPY", "Symbol": "EUR/JPY"},
    {"Pair": "GBP/JPY", "Symbol": "GBP/JPY"},
    {"Pair": "AUD/JPY", "Symbol": "AUD/JPY"},
    {"Pair": "AUD/NZD", "Symbol": "AUD/NZD"},
    {"Pair": "CHF/JPY", "Symbol": "CHF/JPY"},
]

# Timeframe settings
TF_SETTINGS = {
    "Weekly": {"interval": "1week", "outputsize": 104},
    "Daily": {"interval": "1day", "outputsize": 365},
    "H4": {"interval": "4h", "outputsize": 360},
    "H1": {"interval": "1h", "outputsize": 336},
}

# Cache
CACHE: Dict[Tuple[str, str], Tuple[float, Optional[pd.DataFrame]]] = {}
CACHE_TTL = 300  # 5 minutes

def _fetch_twelvedata(symbol: str, interval: str, outputsize: int = 100) -> Optional[pd.DataFrame]:
    """Fetch data from Twelve Data API"""
    key = (symbol, interval)
    now = time.time()
    
    # Check cache
    cached = CACHE.get(key)
    if cached:
        ts, df = cached
        if now - ts < CACHE_TTL:
            log.debug(f"CACHE HIT {symbol} {interval}")
            return df
    
    if not TWELVEDATA_API_KEY:
        log.error("TWELVEDATA_API_KEY not set!")
        return None
    
    try:
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": TWELVEDATA_API_KEY,
            "format": "JSON"
        }
        
        log.info(f"Fetching {symbol} {interval}")
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            log.error(f"API error {response.status_code}: {response.text}")
            return None
        
        data = response.json()
        
        if "values" not in data:
            log.error(f"No values in response: {data}")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(data["values"])
        
        if df.empty:
            log.warning(f"Empty data for {symbol} {interval}")
            return None
        
        # Convert columns
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime").sort_index()
        
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        
        # Rename to standard names
        df = df.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close"
        })
        
        # Cache and return
        CACHE[key] = (now, df)
        return df
        
    except Exception as e:
        log.exception(f"Error fetching {symbol} {interval}: {e}")
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
        
        if tf in ("Weekly", "Daily"):
            ema_period = 200
        elif tf == "H4":
            ema_period = 50
        else:
            ema_period = 20
        
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
        
        # Fetch all timeframes
        for tf, settings in TF_SETTINGS.items():
            df = _fetch_twelvedata(symbol, settings["interval"], settings["outputsize"])
            dfs[tf] = df
            time.sleep(0.5)  # Rate limit friendly
        
        results = {}
        details = {}
        
        for tf in TF_SETTINGS.keys():
            df = dfs.get(tf)
            analysis = _analyze_tf(df, tf)
            label = analysis.get("label") or "No Data"
            results[tf] = label
            details[tf] = analysis
        
        dir_flags = []
        for tf, d in details.items():
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
            "Confluence": {tf: "No Data" for tf in TF_SETTINGS.keys()},
            "ConfluencePercent": 0,
            "Summary": "No Confluence",
            "Details": {}
        }

def get_confluence() -> List[Dict[str, Any]]:
    out = []
    for p in PAIRS:
        sym = p["Symbol"]
        pair_label = p["Pair"]
        log.info(f"Starting confluence for {pair_label} ({sym})")
        res = _compute_for_symbol(sym)
        res["Pair"] = pair_label
        out.append(res)
    return out