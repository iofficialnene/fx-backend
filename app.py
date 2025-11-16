import os
os.environ["YFINANCE_NO_CACHE"] = "1"

from flask import Flask, request, jsonify
import yfinance as yf

app = Flask(__name__)

@app.route("/")
def home():
    return {"status": "running", "message": "FX Confluence backend online"}

@app.route("/price")
def price():
    symbol = request.args.get("symbol", "GBPJPY")
    data = yf.Ticker(symbol).history(period="1d")
    if data.empty:
        return jsonify({"error": "No data"}), 400
    return jsonify({"symbol": symbol, "price": float(data["Close"].iloc[-1])})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
