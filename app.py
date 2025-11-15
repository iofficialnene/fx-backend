from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd

app = Flask(__name__)
CORS(app)

# Full list of symbols (majors, minors, exotics, gold, indices)
pairs = [
    # Majors
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X", "NZDUSD=X", "USDCAD=X",
    # Minors / Exotics
    "EURGBP=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X", "AUDNZD=X", "CHFJPY=X",
    # Gold
    "XAUUSD=X",
    # Indices
    "^GSPC", "^DJI", "^IXIC", "^FTSE", "^N225"
]

def clean_df(df):
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df

def get_trend(data, ema_period=200):
    if data is None or data.empty or "Close" not in data.columns:
        return None
    data['EMA'] = data['Close'].ewm(span=ema_period, adjust=False).mean()
    if data['Close'].iloc[-1] > data['EMA'].iloc[-1]:
        return "Bullish"
    elif data['Close'].iloc[-1] < data['EMA'].iloc[-1]:
        return "Bearish"
    else:
        return "Sideways"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/confluence", methods=["GET"])
def get_confluence():
    results = []
    for symbol in pairs:
        try:
            # Fetch historical data
            weekly = clean_df(yf.download(symbol, period="1y", interval="1wk", progress=False))
            daily = clean_df(yf.download(symbol, period="3mo", interval="1d", progress=False))
            h4 = clean_df(yf.download(symbol, period="1mo", interval="4h", progress=False))
            h1 = clean_df(yf.download(symbol, period="1mo", interval="1h", progress=False))

            # Compute trends
            w_trend = get_trend(weekly)
            d_trend = get_trend(daily)
            h4_trend = get_trend(h4)
            h1_trend = get_trend(h1)

            # Percent confluence
            trends = [w_trend, d_trend, h4_trend, h1_trend]
            trend_count = sum([1 for t in trends if t == trends[0] and t is not None])
            percent_confluence = int((trend_count / 4) * 100)

            # Status
            if percent_confluence == 100:
                status = f"✅ Strong {w_trend}"
            elif percent_confluence >= 50:
                status = f"⚠ Partial ({percent_confluence}%)"
            else:
                status = f"❌ Weak ({percent_confluence}%)"

            results.append({
                "pair": symbol.replace("=X", ""),
                "weekly": w_trend,
                "daily": d_trend,
                "h4": h4_trend,
                "h1": h1_trend,
                "percent": percent_confluence,
                "status": status
            })

        except Exception as e:
            results.append({
                "pair": symbol.replace("=X", ""),
                "status": f"Error: {str(e)}"
            })

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
