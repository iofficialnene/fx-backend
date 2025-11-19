import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from confluence import get_confluence

# App setup
app = Flask(__name__, static_folder="frontend", static_url_path="/")
CORS(app)  # Allow phones + browsers to access API

# API route
@app.route("/confluence")
def confluence_data():
    try:
        data = get_confluence()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Serve frontend (index.html)
@app.route("/")
def serve_frontend():
    return send_from_directory(app.static_folder, "index.html")

# Serve other static files (JS, CSS, images)
@app.route("/<path:path>")
def serve_static_file(path):
    return send_from_directory(app.static_folder, path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)