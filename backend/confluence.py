import yfinance as yf
import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("confluence")

# Correct Yahoo symbols
YF_SYMBOLS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "USDCHF": "CHF=X",
    "AUDUSD": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X",
    "USDCAD": "CAD=X",
    "EURGBP": "EURGBP=X",
    "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X",

    # Crosses not available directly
    "AUDJPY": None,     
    "AUDNZD": None,
    "CHFJPY": None,
    "USDTRY": None,
    "USDZAR": "ZAR=X",
    "USDMXN": "MXN=X",
}

# -------------------------------
# TREND CALC
# -------------------------------
def get_trend(df, tf_name):
    if df is None or len(df) < 5:
        return "No Data"

    df["ma_fast"] = df["Close"].rolling(5).mean()
    df["ma_slow"] = df["Close"].rolling(20).mean()

    last_fast = df["ma_fast"].iloc[-1]
    last_slow = df["ma_slow"].iloc[-1]

    if last_fast > last_slow:
        if (last_fast - last_slow) / last_slow > 0.01:
            return "Strong Bullish"
        return "Bullish"

    if last_fast < last_slow:
        if (last_slow - last_fast) / last_fast > 0.01:
            return "Strong Bearish"
        return "Bearish"

    return "Neutral"


# -------------------------------
# CROSS PAIR BUILDER (AUDNZD, CHFJPY, AUDJPY, USDTRY)
# -------------------------------
def build_cross_pair(pair):
    try:
        if pair == "AUDNZD":
            a = yf.download("AUDUSD=X", period="180d")["Close"]
            n = yf.download("NZDUSD=X", period="180d")["Close"]
            return (a / n).to_frame("Close")

        if pair == "CHFJPY":
            chf = yf.download("CHF=X", period="180d")["Close"]
            jpy = yf.download("JPY=X", period="180d")["Close"]
            return (jpy / chf).to_frame("Close")

        if pair == "AUDJPY":
            aud = yf.download("AUDUSD=X", period="180d")["Close"]
            jpy = yf.download("JPY=X", period="180d")["Close"]
            usd = yf.download("DXY", period="180d")  # fallback
            return (aud * usd["Close"] / jpy).to_frame("Close")

        if pair == "USDTRY":
            try_df = yf.download("TRY=X", period="180d")["Close"]
            return (1 / try_df).to_frame("Close")

    except Exception as e:
        log.error(f"Cross build error for {pair}: {e}")
        return None

    return None


# -------------------------------
# GET DF FOR ANY PAIR
# -------------------------------
def get_df_for_pair(pair):
    symbol = YF_SYMBOLS.get(pair)

    # If it's a cross pair with no direct Yahoo symbol
    if symbol is None:
        df = build_cross_pair(pair)
        if df is None or df.empty:
            log.warning(f"Cross DF failed for {pair}")
        return df

    # Normal yahoo download
    try:
        df = yf.download(symbol, period="180d")
        if df is None or df.empty:
            log.warning(f"Empty DF for {symbol}")
            return None
        return df
    except Exception:
        log.error(f"Failed to get yahoo data for {symbol}")
        return None


# -------------------------------
# MAIN CONFLUENCE CALC
# -------------------------------
def calculate_confluence():
    results = []

    for pair in YF_SYMBOLS.keys():
        df = get_df_for_pair(pair)

        if df is None or df.empty:
            log.warning(f"NO DATA for {pair}")
            results.append({
                "Pair": pair,
                "Confluence": {},
                "ConfluencePercent": 0
            })
            continue

        # Timeframes (resampled)
        week = df.resample("W").last()
        day = df.resample("1D").last()
        h4 = df.resample("4H").last()
        h1 = df.resample("1H").last()

        confluences = {
            "Weekly": get_trend(week, "Weekly"),
            "Daily": get_trend(day, "Daily"),
            "H4": get_trend(h4, "H4"),
            "H1": get_trend(h1, "H1"),
        }

        # Calculate points
        score_map = {
            "Strong Bullish": 3,
            "Bullish": 2,
            "Neutral": 1,
            "Bearish": 2,
            "Strong Bearish": 3
        }

        score = sum(score_map.get(v, 0) for v in confluences.values())
        pct = int((score / (3 * 4)) * 100)  # max = 12 points → 100%

        results.append({
            "Pair": pair,
            "Confluence": confluences,
            "ConfluencePercent": pct
        })

    return results