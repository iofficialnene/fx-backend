from flask import Flask, jsonify, render_template
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
CORS(app)

# Full list of symbols (majors, minors, exotics, gold, indices)
pairs = [
    "EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","AUDUSD=X","USDCAD=X","NZDUSD=X",
    "EURJPY=X","GBPJPY=X","AUDJPY=X","EURGBP=X","XAUUSD","^GSPC","^DJI"
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

def get_chart(data):
    if data is None or data.empty:
        return ""
    fig, ax = plt.subplots()
    data['Close'].plot(ax=ax)
    ax.set_title("Price Chart")
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return img_base64

@app.route("/confluence")
def confluence():
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

            percent_confluence = sum([t is not None and t==w_trend for t in [d_trend,h4_trend,h1_trend]]) / 3 * 100 if w_trend else 0
            chart = get_chart(daily)

            results.append({
                "pair": symbol.replace("=X",""),
                "weekly": w_trend,
                "daily": d_trend,
                "h4": h4_trend,
                "h1": h1_trend,
                "percent_confluence": percent_confluence,
                "chart": chart,
                "status": "✅ Strong" if percent_confluence==100 else "❌ Partial" if percent_confluence>0 else "❌ No Data"
            })
        except Exception as e:
            results.append({"pair": symbol.replace("=X",""), "status": f"Error: {e}"})
    return jsonify(results)

@app.route("/")
def index():
    return render_template("index.html")  # Include auto-refresh + filters in index.html

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
