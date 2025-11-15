from flask import Flask, render_template, jsonify
import your_confluence_module  # whatever you use to get confluence data

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/confluence")
def confluence_data():
    # Example: return JSON in the structure your JS expects
    data = your_confluence_module.get_confluence()  
    # Example format:
    # [
    #   {"Pair": "EURUSD=X", "Confluence": {"Weekly": "Strong Bullish", "Daily": "Bullish", ...}},
    #   ...
    # ]
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
