from flask import Flask, jsonify, render_template
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
CORS(app)

# Currency pairs + gold + indices
pairs = [
    "EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","AUDUSD=X","USDCAD=X","NZDUSD=X",
    "EURJPY=X","GBPJPY=X","AUDJPY=X","GBPCHF=X","XAUUSD=X", # Gold
    "^GSPC","^DJI","^IXIC" # Indices
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

def generate_chart(symbol):
    df = clean_df(yf.download(symbol, period="1mo", interval="1d", progress=False))
    if df.empty:
        return None
    plt.figure(figsize=(5,2))
    plt.plot(df.index, df['Close'], label='Close')
    plt.title(symbol.replace("=X",""))
    plt.legend()
    plt.tight_layout()
    img = io.BytesIO()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode()

@app.route("/confluence")
def get_confluence():
    results = []
    for symbol in pairs:
        try:
            weekly = clean_df(yf.download(symbol, period="1y", interval="1wk", progress=False))
            daily = clean_df(yf.download(symbol, period="3mo", interval="1d", progress=False))
            h4 = clean_df(yf.download(symbol, period="1mo", interval="4h", progress=False))
            h1 = clean_df(yf.download(symbol, period="1mo", interval="1h", progress=False))

            trends = [get_trend(weekly), get_trend(daily), get_trend(h4), get_trend(h1)]
            percent_confluence = len([t for t in trends if t is not None and t == trends[0]]) / 4 * 100

            if all(t == trends[0] and t is not None for t in trends):
                status = f"✅ Strong {trends[0]}"
            elif any(t is not None for t in trends):
                status = f"⚠️ Partial Confluence ({percent_confluence:.0f}%)"
            else:
                status = "❌ No Data"

            chart = generate_chart(symbol)

            results.append({
                "pair": symbol.replace("=X",""),
                "weekly": trends[0],
                "daily": trends[1],
                "h4": trends[2],
                "h1": trends[3],
                "percent_confluence": percent_confluence,
                "status": status,
                "chart": chart
            })
        except Exception as e:
            results.append({"pair": symbol.replace("=X",""), "status": f"Error: {str(e)}"})
    return jsonify(results)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
