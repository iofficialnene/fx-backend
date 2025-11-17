# app.py
from flask import Flask, jsonify, send_from_directory
from confluence import get_confluence

app = Flask(__name__, static_folder="frontend", static_url_path="/")

@app.route("/confluence")
def confluence_data():
    data = get_confluence()
    return jsonify(data)

# Serve frontend static index.html at root (if you built frontend into 'frontend' dir)
@app.route("/")
def serve_frontend():
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    # allow Render or Docker to set PORT via env var
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
