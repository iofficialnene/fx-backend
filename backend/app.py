# backend/app.py
import os
import traceback
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from confluence import get_confluence

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to built frontend (adjust if needed)
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")

app = Flask(
    __name__,
    static_folder=FRONTEND_DIST,
    static_url_path="/"
)

# Allow all domains to call /confluence
CORS(app, resources={r"/confluence": {"origins": "*"}})


# -----------------------------------------------------
# GET CONFLUENCE DATA (MAIN API)
# -----------------------------------------------------
@app.route("/confluence")
def confluence_route():
    try:
        data = get_confluence()

        # FAILSAFE: if function returns None or empty, warn frontend
        if not data:
            return jsonify({
                "error": "No confluence data returned",
                "data": data
            }), 500

        return jsonify(data)

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": "Backend crashed inside get_confluence",
            "detail": str(e),
            "trace": traceback.format_exc()
        }), 500


# -----------------------------------------------------
# HEALTH CHECK
# -----------------------------------------------------
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "port": str(os.environ.get("PORT", "no-port"))
    })


# -----------------------------------------------------
# SERVE FRONTEND (VITE/REACT)
# -----------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Serve the Vite-built React frontend from /frontend/dist"""

    # If file exists in dist, serve it
    if path and os.path.exists(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)

    # Otherwise serve index.html (SPA fallback)
    return send_from_directory(FRONTEND_DIST, "index.html")


# -----------------------------------------------------
# START
# -----------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
