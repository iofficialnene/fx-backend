# backend/app.py
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from confluence import get_confluence

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")  # adjust if your built frontend is elsewhere

app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path="/")
CORS(app, resources={r"/confluence": {"origins": "*"}})

@app.route("/confluence")
def confluence_route():
    try:
        data = get_confluence()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    return jsonify({"status":"ok","time":str(os.environ.get("PORT", "no-port"))})

# serve frontend files
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    index_path = os.path.join(app.static_folder, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(app.static_folder, "index.html")
    return jsonify({"message":"No frontend built - visit /confluence to see JSON"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
