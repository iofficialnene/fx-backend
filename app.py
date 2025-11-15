from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd

app = Flask(__name__)
CORS(app)

pairs = [
    "EURUSD=X", "GBPJPY=X", "USDCHF=X", "AUDUSD=X",
    "USDCAD=X", "NZDUSD=X", "EURJPY=X", "GBPUSD=X"
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

@app.route("/confluence", methods=["GET"])
def get_confluence():
    results = []
    for symbol in pairs:
        try:
            weekly = clean_df(yf.download(symbol, period="1y", interval="1wk", progress=False))
            daily = clean_df(yf.download(symbol, period="3mo", interval="1d", progress=False))
            h4 = clean_df(yf.download(symbol, period="1mo", interval="4h", progress=False))
            h1 = clean_df(yf.download(symbol, period="1mo", interval="1h", progress=False))

            w_trend = get_trend(weekly)
            d_trend = get_trend(daily)
            h4_trend = get_trend(h4)
            h1_trend = get_trend(h1)

            # Confluence logic
            if w_trend == d_trend == h4_trend == h1_trend and w_trend is not None:
                status = f"✅ Strong {w_trend}"
            elif any([w_trend, d_trend, h4_trend, h1_trend]):
                status = "❌ Partial Confluence"
            else:
                status = "❌ No Data"

            results.append({
                "pair": symbol.replace("=X", ""),
                "weekly": w_trend,
                "daily": d_trend,
                "h4": h4_trend,
                "h1": h1_trend,
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
