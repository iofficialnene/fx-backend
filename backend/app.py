import os
from flask import Flask, jsonify
from flask_cors import CORS
from confluence import get_confluence

app = Flask(__name__)
CORS(app)

@app.route("/confluence")
def confluence_data():
    try:
        return jsonify(get_confluence())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return {"status": "Backend running"}

if __name__ == "__main__":
    port = os.environ.get("PORT")
    if port is None or not port.isdigit():
        port = 5000  # fallback for local testing
    app.run(host="0.0.0.0", port=int(port))
