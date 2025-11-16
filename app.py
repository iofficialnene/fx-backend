# app.py
import os
from flask import Flask, render_template, jsonify
from confluence import get_confluence

app = Flask(__name__, static_folder="static", template_folder="templates")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/confluence")
def confluence_data():
    data = get_confluence()
    return jsonify(data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
