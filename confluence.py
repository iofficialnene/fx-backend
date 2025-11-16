# confluence.py
import os
import math
import time
import traceback
from typing import List, Dict
import pandas as pd
import numpy as np
import yfinance as yf
import requests

TD_API_KEY = os.environ.get("TD_API_KEY", "").strip()

# Pairs/groups (you asked: majors, minors, exotics, indices, gold)
PAIRS = [
    # Majors
    {"Pair": "EUR/USD", "Symbol": "EURUSD=X"},
    {"Pair": "GBP/USD", "Symbol": "GBPUSD=X"},
    {"Pair": "USD/JPY", "Symbol": "JPY=X"},          # yfinance uses JPY=X for USD/JPY
    {"Pair": "USD/CHF", "Symbol": "CHF=X"},
    {"Pair": "AUD/USD", "Symbol": "AUDUSD=X"},
    {"Pair": "NZD/USD", "Symbol": "NZDUSD=X"},
    {"Pair": "USD/CAD", "Symbol": "CAD=X"},
    # Crosses / minors
    {"Pair": "EUR/GBP", "Symbol": "EURGBP=X"},
    {"Pair": "EUR/JPY", "Symbol": "EURJPY=X"},
    {"Pair": "GBP/JPY", "Symbol": "GBPJPY=X"},
    {"Pair": "AUD/JPY", "Symbol": "AUDJPY=X"},
    {"Pair": "AUD/NZD", "Symbol": "AUDNZD=X"},
    {"Pair": "CHF/JPY", "Symbol": "CHFJPY=X"},
    # Exotics (examples)
    {"Pair": "USD/SGD", "Symbol": "USDSGD=X"},
    {"Pair": "USD/TRY", "Symbol": "USDTRY=X"},
    {"Pair": "USD/ZAR", "Symbol": "USDZAR=X"},
    # Indices (yfinance tickers; these sometimes fail if provider blocks, but we try)
    {"Pair": "S&P 500", "Symbol": "^GSPC"},
    {"Pair": "Dow Jones", "Symbol": "^DJI"},
    {"Pair": "Nasdaq 100", "Symbol": "^NDX"},
    {"Pair": "FTSE 100", "Symbol": "^FTSE"},
    {"Pair": "DAX", "Symbol": "^GDAXI"},
    # Commodities / Gold
    {"Pair": "Gold", "Symbol": "GC=F"},     # futures
    {"Pair": "XAU/USD", "Symbol": "XAUUSD=X"},  # sometimes works
]

# timeframe mapping: label -> yfinance interval & period
TF_CONFIG = {
    "Weekly": {"interval": "1wk", "period": "2y"},
    "Daily":  {"interval": "1d",  "period": "1y"},
    "H4":     {"interval": "4h",  "period": "180d"},
    "H1":     {"interval": "1h",  "period": "60d"},
}

def fetch_yf(symbol: str, interval: str, period: str) -> pd.DataFrame:
    """
    Try to fetch with yfinance. Returns DataFrame or empty DF on failure.
    """
    try:
        # yfinance may accept symbol 'JPY=X' for USD/JPY already reversed mapping above
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=False)
        if df.empty:
            return pd.DataFrame()
        # ensure float columns
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df.dropna(inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

def fetch_twelvedata(symbol: str, interval: str) -> pd.DataFrame:
    """
    Fallback to Twelve Data only if TD_API_KEY is provided.
    Twelve Data symbol formatting typically uses 'EUR/USD' for forex — we will try both.
    """
    if not TD_API_KEY:
        return pd.DataFrame()
    # map yfinance interval to Twelve Data interval naming
    td_interval = {
        "1wk": "1week", "1d": "1day", "4h": "4h", "1h": "1h"
    }.get(interval, interval)
    # try symbol variants
    possible_symbols = [symbol]
    if symbol.endswith("=X"):
        possible_symbols.append(symbol.replace("=X","").replace("USD","/USD"))
        possible_symbols.append(symbol.replace("=X","").replace("USD","/USD"))
    if "/" not in symbol:
        possible_symbols.append(symbol.replace("=X","").replace("^",""))
        possible_symbols.append(symbol.replace("=X","").replace("^",""))
    for s in possible_symbols:
        try:
            url = "https://api.twelvedata.com/time_series"
            params = {"symbol": s, "interval": td_interval, "outputsize": 500, "apikey": TD_API_KEY}
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
            if "values" in data:
                df = pd.DataFrame(data["values"])
                # TD returns newest first; reverse
                df = df.iloc[::-1].reset_index(drop=True)
                df = df.rename(columns={"open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"})
                for col in ["Open","High","Low","Close","Volume"]:
                    if col in df:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                df.dropna(inplace=True)
                return df[['Open','High','Low','Close','Volume']].copy()
        except Exception:
            continue
    return pd.DataFrame()

def get_series(symbol: str, interval: str, period: str) -> pd.DataFrame:
    df = fetch_yf(symbol, interval, period)
    if df.empty:
        df = fetch_twelvedata(symbol, interval)
    return df

def analyze_series(df: pd.DataFrame) -> Dict:
    """
    Compute EMA200-based trend and simple BOS (last candle high/low vs previous).
    Returns dict with 'trend_text' and 'bos' etc.
    """
    if df.empty or len(df) < 10:
        return {"trend": "", "trend_text": "", "distance_pct": 0.0, "bos": ""}

    close = df['Close'].astype(float)
    high = df['High'].astype(float)
    low = df['Low'].astype(float)

    # EMA200 (use ewm span=200)
    ema200 = close.ewm(span=200, adjust=False).mean()
    last_close = close.iloc[-1]
    last_ema = ema200.iloc[-1]
    # distance pct
    distance_pct = ((last_close - last_ema) / last_ema) * 100 if last_ema != 0 else 0.0

    # Trend classification
    trend = ""
    trend_text = ""
    if last_close > last_ema:
        # bullish
        if distance_pct > 1.0:
            trend = "Strong Bullish"
        else:
            trend = "Bullish"
    elif last_close < last_ema:
        if distance_pct < -1.0:
            trend = "Strong Bearish"
        else:
            trend = "Bearish"
    else:
        trend = ""

    # Simple BOS detection: compare last high/low vs previous candle high/low
    bos = ""
    if len(high) >= 2:
        if high.iloc[-1] > high.iloc[-2] and close.iloc[-1] > close.iloc[-2]:
            bos = "BOS_up"
        elif low.iloc[-1] < low.iloc[-2] and close.iloc[-1] < close.iloc[-2]:
            bos = "BOS_down"

    return {
        "trend": trend,
        "trend_text": f"{trend} ({distance_pct:.2f}%)" if trend else "",
        "distance_pct": float(round(distance_pct, 4)),
        "bos": bos
    }

def get_confluence() -> List[Dict]:
    """
    Main: for each pair, fetch each TF, analyze, compute confluence% and return list.
    """
    results = []
    for p in PAIRS:
        pair_label = p["Pair"]
        symbol = p["Symbol"]

        confluence = {}
        counts = {"bull": 0, "bear": 0, "valid": 0}
        tf_results = {}

        for tf_label, cfg in TF_CONFIG.items():
            df = get_series(symbol, cfg["interval"], cfg["period"])
            analysis = analyze_series(df)
            trend_text = analysis["trend_text"]
            if analysis["trend"] in ("Bullish", "Strong Bullish"):
                counts["bull"] += 1
                counts["valid"] += 1
            elif analysis["trend"] in ("Bearish", "Strong Bearish"):
                counts["bear"] += 1
                counts["valid"] += 1
            tf_results[tf_label] = analysis["trend_text"] + (f" {analysis['bos']}" if analysis['bos'] else "")

            # small delay to avoid fast request bursts
            time.sleep(0.05)

        # Confluence percent = % of timeframes that are bullish OR bearish (same direction not required)
        confluence_count = counts["valid"]
        total = len(TF_CONFIG)
        confluence_pct = int(round((confluence_count / total) * 100)) if total else 0

        # Summary determination: if majority bulls -> Bullish / Strong Bullish if many strong
        summary = "No Confluence"
        if counts["valid"] >= 1:
            # simple majority sign by net = bull - bear
            net = counts["bull"] - counts["bear"]
            if net > 0:
                summary = "Bullish"
                # upgrade to Strong if 3 or 4 TFs bullish
                if counts["bull"] >= 3:
                    summary = "Strong Bullish"
            elif net < 0:
                summary = "Bearish"
                if counts["bear"] >= 3:
                    summary = "Strong Bearish"
            else:
                summary = "Mixed"

        results.append({
            "Pair": pair_label,
            "Symbol": symbol,
            "Confluence": tf_results,
            "ConfluencePercent": confluence_pct,
            "Summary": summary
        })

    return results
