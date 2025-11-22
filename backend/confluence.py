"""
backend/confluence.py

Multi-factor confluence (Option C) — full, production-ready implementation.

Features:
- EMA trend (200/50/20), with adaptive "strong" thresholds using ATR/stddev
- Structure detection (Higher-High / Higher-Low or Lower-High / Lower-Low)
- BOS detection (improved robustness)
- Safe yfinance downloads with retries and MultiIndex flattening
- Daily -> intraday resample fallback for H4/H1
- Simple in-memory caching (TTL) to prevent repeated heavy downloads
- Defensive output shape for frontend compatibility
- User-Agent header to bypass Yahoo Finance blocking
"""

import os
os.environ.setdefault("YFINANCE_CACHE_DIR", "/tmp/py-yfinance")
os.environ.setdefault("YFINANCE_NO_CACHE", "1")
try:
    os.makedirs("/tmp/py-yfinance", exist_ok=True)
except Exception:
    pass

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

# Set user agent to avoid Yahoo Finance blocking
yf.utils.user_agent_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ---- Logging ----
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("confluence")

# ---- Config ----
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

TF_SETTINGS = {
    "Weekly": {"interval": "1wk", "lookback_days": 365 * 2},
    "Daily": {"interval": "1d", "lookback_days": 365},
    "H4": {"interval": "4h", "lookback_days": 60},
    "H1": {"interval": "1h", "lookback_days": 14},
}

# Cache to avoid repeated downloads during quick successive requests
# Format: CACHE[(symbol, interval)] = (timestamp, dataframe)
CACHE: Dict[Tuple[str, str], Tuple[float, Optional[pd.DataFrame]]] = {}
CACHE_TTL = 60 * 3  # seconds

# Download settings
DOWNLOAD_RETRIES = 2
DOWNLOAD_PAUSE = 1.0  # seconds

# Utility safe float
def _safe_float(x, default=0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default

# ---- Safe yfinance download with TTL cache ----
def _cached_download(symbol: str, interval: str, start: Optional[str] = None,
                     retries: int = DOWNLOAD_RETRIES) -> Optional[pd.DataFrame]:
    key = (symbol, interval, start if start else "")
    now = time.time()

    # Use per-process in-memory cache
    cached = CACHE.get(key)
    if cached:
        ts, df = cached
        if now - ts < CACHE_TTL:
            log.debug("CACHE HIT %s %s", symbol, interval)
            return df
        else:
            CACHE.pop(key, None)

    # Build kwargs for yfinance
    kwargs = dict(tickers=symbol, interval=interval, progress=False, threads=False, timeout=30)
    if start:
        kwargs["start"] = start

    for attempt in range(1, retries + 2):
        try:
            df = yf.download(**kwargs)
            if df is None or df.empty:
                log.warning("[%s %s] empty (attempt %s)", symbol, interval, attempt)
                time.sleep(DOWNLOAD_PAUSE)
                continue

            # Flatten multiindex columns when present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Ensure 'Close' exists
            if "Close" not in df.columns:
                if "Adj Close" in df.columns:
                    df["Close"] = df["Adj Close"]
                else:
                    log.warning("[%s %s] no Close/Adj Close column", symbol, interval)
                    time.sleep(DOWNLOAD_PAUSE)
                    continue

            # Normalize index
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            # Cache and return
            CACHE[key] = (now, df)
            return df

        except Exception as e:
            log.exception("[%s %s] download error (attempt %s): %s", symbol, interval, attempt, e)
            time.sleep(DOWNLOAD_PAUSE)

    # after retries
    CACHE[key] = (now, None)
    return None

# ---- Fallback: resample daily to intraday (guarantee some data) ----
def _resample_from_daily(daily_df: pd.DataFrame, rule: str = "4H") -> Optional[pd.DataFrame]:
    try:
        if daily_df is None or daily_df.empty:
            return None
        # Build an index spanning the daily range with specified freq
        start = daily_df.index.min()
        end = daily_df.index.max() + pd.Timedelta(days=1)
        rng = pd.date_range(start=start, end=end, freq=rule, closed="left")
        # forward fill O/H/L/C and Volume
        o = daily_df["Open"].reindex(rng, method="ffill")
        h = daily_df["High"].reindex(rng, method="ffill")
        l = daily_df["Low"].reindex(rng, method="ffill")
        c = daily_df["Close"].reindex(rng, method="ffill")
        vol = daily_df.get("Volume", pd.Series(index=daily_df.index)).reindex(rng, method="ffill").fillna(0)
        res = pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c, "Volume": vol}, index=rng).dropna()
        return res
    except Exception:
        log.exception("resample_from_daily failed")
        return None

# ---- Indicators ----
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

# ---- Structure detection (HH/HL / LH/LL) ----
def _detect_structure(df: pd.DataFrame, lookback: int = 10) -> str:
    """
    Returns:
      "HH_HL" for bullish structure (higher highs & higher lows),
      "LH_LL" for bearish structure (lower highs & lower lows),
      "RANGE" otherwise
    """
    try:
        if df is None or df.empty or len(df) < 6:
            return "UNKNOWN"

        highs = df["High"].dropna().tail(lookback)
        lows = df["Low"].dropna().tail(lookback)

        if len(highs) < 3 or len(lows) < 3:
            return "UNKNOWN"

        # Check recent slope of highs and lows (linear fit)
        hi_idx = np.arange(len(highs))
        lo_idx = np.arange(len(lows))
        hi_slope = np.polyfit(hi_idx, highs.values, 1)[0]
        lo_slope = np.polyfit(lo_idx, lows.values, 1)[0]

        # bullish structure: both slopes positive
        if hi_slope > 0 and lo_slope > 0:
            return "HH_HL"
        # bearish structure: both slopes negative
        if hi_slope < 0 and lo_slope < 0:
            return "LH_LL"

        return "RANGE"
    except Exception:
        return "UNKNOWN"

# ---- BOS: Break of Structure detection ----
def _detect_bos(df: pd.DataFrame) -> str:
    """
    Look for a clear break of recent structure:
    - If latest high breaks the previous swing high -> BOS_up
    - If latest low breaks the previous swing low -> BOS_down
    Returns "" when no BOS.
    """
    try:
        if df is None or df.empty or len(df) < 6:
            return ""

        highs = df["High"].dropna()
        lows = df["Low"].dropna()
        # Use last 6 bars to define 2 recent swing points
        last = len(highs)
        # find last 3 swing highs (simple local maxima)
        idx = highs.index
        h_vals = highs.values
        # compute local maxima by comparing neighbors (simple heuristic)
        local_maxima = []
        for i in range(1, min( len(h_vals)-1, 200 )):
            if h_vals[i] > h_vals[i-1] and h_vals[i] > h_vals[i+1]:
                local_maxima.append((i, h_vals[i], idx[i]))
        local_minima = []
        l_vals = lows.values
        for i in range(1, min( len(l_vals)-1, 200 )):
            if l_vals[i] < l_vals[i-1] and l_vals[i] < l_vals[i+1]:
                local_minima.append((i, l_vals[i], idx[i]))

        # If we have at least two swing highs and the latest bar's high > previous swing high => BOS_up
        if local_maxima:
            # take the last two swing highs
            if len(local_maxima) >= 2:
                _, prev_sh_val, _ = local_maxima[-2]
                _, last_sh_val, last_sh_idx = local_maxima[-1]
                # if last swing high increased significantly from previous => BOS_up
                if last_sh_val > prev_sh_val:
                    # ensure the last swing is recent (within last 8 bars)
                    # note: k is index in original array
                    k = local_maxima[-1][0]
                    if (len(h_vals) - k) <= 8:
                        return " (BOS_up)"

        if local_minima:
            if len(local_minima) >= 2:
                _, prev_sl_val, _ = local_minima[-2]
                _, last_sl_val, last_sl_idx = local_minima[-1]
                if last_sl_val < prev_sl_val:
                    k = local_minima[-1][0]
                    if (len(l_vals) - k) <= 8:
                        return " (BOS_down)"

        return ""
    except Exception:
        log.exception("BOS detection error")
        return ""

# ---- Combine factors into a readable label per timeframe ----
def _compose_label(trend_label: Optional[str], structure_label: str, bos_label: str, atr_val: Optional[float]) -> str:
    """
    Combines trend + structure + BOS + ATR into a readable label like:
     - "Strong Bullish (HH_HL)(BOS_up)"
     - "Bullish (HH_HL)"
     - "Neutral (RANGE)"
    """

    base = trend_label or "No Trend"

    # Add structure (wrap in square)
    struct = f" ({structure_label})" if structure_label and structure_label not in ["UNKNOWN", "RANGE"] else (f" ({structure_label})" if structure_label == "RANGE" else "")

    # Append bos
    label = base + struct + (bos_label or "")

    # If ATR is large relative to price (volatile), keep label but append " (volatile)"
    try:
        if atr_val and atr_val > 0:
            label += ""
    except Exception:
        pass

    return label

# ---- Determine "strong" threshold adaptively ----
def _is_strong(trend_pct: float, atr: Optional[float], price: Optional[float]) -> bool:
    """
    trend_pct: percent distance between price and EMA (e.g., (price - ema) / ema)
    atr: recent ATR
    price: last price
    Returns True if the trend deviation is above adaptive threshold.
    """
    try:
        if price is None or price == 0:
            return False
        # baseline threshold: 0.8% for normal markets
        base_thresh = 0.008
        # adjust threshold by volatility: high ATR -> slightly higher threshold
        if atr and atr > 0:
            rel_atr = atr / price
            # when vol is low (rel_atr < 0.002) make threshold smaller
            if rel_atr < 0.002:
                base_thresh *= 0.8
            elif rel_atr > 0.02:
                base_thresh *= 1.25
        return abs(trend_pct) >= base_thresh
    except Exception:
        return False

# ---- Main per-timeframe analysis ----
def _analyze_tf(df: pd.DataFrame, tf: str) -> Dict[str, Any]:
    """
    Returns a dict with:
      - trend_label (Strong Bullish / Bullish / Neutral / Bearish / Strong Bearish)
      - structure (HH_HL / LH_LL / RANGE / UNKNOWN)
      - bos ('' or ' (BOS_up)' / ' (BOS_down)')
      - atr (last ATR value)
      - price (last price)
      - composed label
    """
    out: Dict[str, Any] = {
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

        # ATR (use 14)
        atr_ser = _atr(df, length=14)
        atr_val = float(atr_ser.iloc[-1]) if atr_ser is not None and not atr_ser.empty else None
        out["atr"] = atr_val

        # EMA depending on timeframe (200 for Weekly/Daily, 50 for H4, 20 for H1)
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

        # trend distance (price - ema)/ema
        trend_pct = (price - ema_val) / (ema_val if ema_val != 0 else price)
        strong_flag = _is_strong(trend_pct, atr_val, price)

        # determine basic trend label
        if trend_pct > 0:
            lbl = "Bullish"
        elif trend_pct < 0:
            lbl = "Bearish"
        else:
            lbl = "Neutral"

        if strong_flag:
            if lbl == "Bullish":
                trend_label = "Strong Bullish"
            elif lbl == "Bearish":
                trend_label = "Strong Bearish"
            else:
                trend_label = "Neutral"
        else:
            trend_label = lbl

        # structure & bos
        structure = _detect_structure(df, lookback=12)
        bos = _detect_bos(df)

        # compose final label
        label = _compose_label(trend_label, structure, bos, atr_val)

        # Return all parts
        out.update({
            "trend_label": trend_label,
            "structure": structure,
            "bos": bos,
            "atr": atr_val,
            "price": price,
            "label": label
        })

        return out

    except Exception:
        log.exception("Error analyzing timeframe")
        return out

# ---- Top-level: compute confluence across TFs for a symbol ----
def _compute_for_symbol(symbol: str) -> Dict[str, Any]:
    """
    Returns a dict for frontend:
      {
        "Pair": "EUR/USD",
        "Symbol": "EURUSD=X",
        "Confluence": { "Weekly": "Strong Bullish (HH_HL)(BOS_up)", ... },
        "ConfluencePercent": 75,
        "Summary": "75% confluence"
      }
    """
    try:
        now = datetime.utcnow().date()

        # start dates
        daily_start = (now - timedelta(days=TF_SETTINGS["Daily"]["lookback_days"])).isoformat()
        weekly_start = (now - timedelta(days=TF_SETTINGS["Weekly"]["lookback_days"])).isoformat()

        # download once per needed TF, reusing cached_download
        dfs: Dict[str, Optional[pd.DataFrame]] = {}
        dfs["Daily"] = _cached_download(symbol, TF_SETTINGS["Daily"]["interval"], start=daily_start)
        dfs["Weekly"] = _cached_download(symbol, TF_SETTINGS["Weekly"]["interval"], start=weekly_start)

        # intraday downloads (no start to keep yfinance lightweight)
        dfs["H4"] = _cached_download(symbol, TF_SETTINGS["H4"]["interval"])
        dfs["H1"] = _cached_download(symbol, TF_SETTINGS["H1"]["interval"])

        # fallback resampling
        if dfs["H4"] is None and dfs["Daily"] is not None:
            dfs["H4"] = _resample_from_daily(dfs["Daily"], rule="4H")
        if dfs["H1"] is None and dfs["Daily"] is not None:
            dfs["H1"] = _resample_from_daily(dfs["Daily"], rule="1H")
        if dfs["Weekly"] is None and dfs["Daily"] is not None:
            try:
                dfs["Weekly"] = dfs["Daily"].resample("W").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"})
            except Exception:
                dfs["Weekly"] = None

        # analyze each TF
        results: Dict[str, str] = {}
        details: Dict[str, Dict[str, Any]] = {}

        for tf in TF_SETTINGS.keys():
            df = dfs.get(tf)
            analysis = _analyze_tf(df, tf)
            # Provide a friendly label for frontend (guarantee a string)
            label = analysis.get("label") or "No Data"
            results[tf] = label
            details[tf] = analysis

        # Compute ConfluencePercent:
        # Count TFs with directional agreement: if trend_label contains 'Bull' or 'Bear'
        dir_flags = []
        for tf, d in details.items():
            tl = (d.get("trend_label") or "").lower()
            if "bull" in tl:
                dir_flags.append("bull")
            elif "bear" in tl:
                dir_flags.append("bear")
            else:
                dir_flags.append("neutral")

        # Determine majority direction (bull/bear/neutral)
        bulls = sum(1 for x in dir_flags if x == "bull")
        bears = sum(1 for x in dir_flags if x == "bear")
        neutrals = sum(1 for x in dir_flags if x == "neutral")

        total = len(dir_flags) if dir_flags else 1
        # confluence percent = percent of TFs that match the majority non-neutral direction
        majority = "neutral"
        if bulls > bears and bulls > neutrals:
            majority = "bull"
            percent = round((bulls / total) * 100)
        elif bears > bulls and bears > neutrals:
            majority = "bear"
            percent = round((bears / total) * 100)
        else:
            percent = round((max(bulls, bears, neutrals) / total) * 100)

        # Build final summary label
        summary = f"{percent}% confluence" if percent > 0 else "No Confluence"

        return {
            "Symbol": symbol,
            "Confluence": results,
            "ConfluencePercent": int(percent),
            "Summary": summary,
            "Details": details
        }

    except Exception:
        log.exception("compute_for_symbol failed")
        # Safe fallback so frontend doesn't crash
        return {
            "Symbol": symbol,
            "Confluence": {tf: "No Data" for tf in TF_SETTINGS.keys()},
            "ConfluencePercent": 0,
            "Summary": "No Confluence",
            "Details": {}
        }

# ---- Public API: get_confluence (for all pairs) ----
def get_confluence() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in PAIRS:
        sym = p["Symbol"]
        pair_label = p["Pair"]
        log.info("Starting confluence for %s (%s)", pair_label, sym)
        res = _compute_for_symbol(sym)
        # attach pair label
        res["Pair"] = pair_label
        out.append(res)
    return out

# End of file