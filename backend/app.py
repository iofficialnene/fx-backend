from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from confluence_data import get_confluence

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')
CORS(app)

@app.route("/confluence")
def confluence_api():
    # Returns list of pair dicts
    data = get_confluence()
    return jsonify(data)

# Optional: serve the frontend build from backend (if you want single deploy)
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path != "" and (app.static_folder / path).exists():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(__import__("os").environ.get("PORT", 5000)), debug=True)
