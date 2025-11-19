import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from confluence import get_confluence

app = Flask(__name__, static_folder="frontend", static_url_path="/")
CORS(app)

@app.route("/confluence")
def confluence_route():
    try:
        return jsonify(get_confluence())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def root():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
