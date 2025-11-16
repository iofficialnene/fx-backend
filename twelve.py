import os
import yfinance as yf
from flask import Flask, jsonify

# -------------------------------
# FIX YFINANCE CACHE CRASH (Render)
# -------------------------------
CACHE_DIR = "/tmp/yf-cache"
os.environ["YFINANCE_CACHE_DIR"] = CACHE_DIR
os.makedirs(CACHE_DIR, exist_ok=True)

app = Flask(__name__)

# -------------------------------
# ALL PAIRS + INDICES + GOLD
# -------------------------------
PAIRS = {
    # Majors
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X",
    "USD/CHF": "CHF=X", "USD/CAD": "CAD=X", "AUD/USD": "AUDUSD=X", "NZD/USD": "NZDUSD=X",

    # Minors
    "EUR/GBP": "EURGBP=X", "EUR/AUD": "EURAUD=X", "EUR/NZD": "EURNZD=X",
    "GBP/JPY": "GBPJPY=X", "GBP/CHF": "GBPCHF=X", "AUD/JPY": "AUDJPY=X",
    "NZD/JPY": "NZDJPY=X", "CHF/JPY": "CHFJPY=X",

    # Exotics
    "USD/TRY": "TRY=X", "USD/ZAR": "ZAR=X", "USD/MXN": "MXN=X",
    "EUR/TRY": "EURTRY=X", "USD/SEK": "SEK=X", "USD/NOK": "NOK=X",

    # Metals
    "XAU/USD (Gold)": "GC=F",

    # Indices
    "US30": "^DJI", "US100": "^NDX", "US500": "^GSPC",
    "DAX": "^GDAXI", "FTSE100": "^FTSE"
}

# -------------------------------
# SAFELY FETCH TREND
# -------------------------------
def get_trend(symbol, period):
    try:
        data = yf.Ticker(symbol).history(period=period)

        if data.empty:
            return ""  # no crash

        close = data["Close"]
        if close.iloc[-1] > close.iloc[0]:
            return "Bullish"
        elif close.iloc[-1] < close.iloc[0]:
            return "Bearish"
        else:
            return "Neutral"

    except:
        return ""  # fail safe


# -------------------------------
# CALCULATE CONFLUENCE
# -------------------------------
def calculate_confluence(symbol):
    tf = {
        "Weekly": get_trend(symbol, "3mo"),
        "Daily": get_trend(symbol, "1mo"),
        "H4": get_trend(symbol, "60d"),
        "H1": get_trend(symbol, "10d")
    }

    # Count trends
    bulls = list(tf.values()).count("Bullish")
    bears = list(tf.values()).count("Bearish")

    # Summary
    if bulls == 4:
        summary = "Strong Bullish"
        pct = 100
    elif bears == 4:
        summary = "Strong Bearish"
        pct = 100
    elif bulls >= 3:
        summary = "Bullish Bias"
        pct = 75
    elif bears >= 3:
        summary = "Bearish Bias"
        pct = 75
    else:
        summary = "No Confluence"
        pct = 0

    return tf, pct, summary


# -------------------------------
# API ROUTE
# -------------------------------
@app.route("/api/confluence", methods=["GET"])
def confluence_api():
    output = []

    for pair, symbol in PAIRS.items():
        tf, pct, summary = calculate_confluence(symbol)

        output.append({
            "Pair": pair,
            "Symbol": symbol,
            "Confluence": tf,
            "ConfluencePercent": pct,
            "Summary": summary
        })

    return jsonify(output)


# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
