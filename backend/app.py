from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from confluence import get_confluence

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

@app.route("/api/confluence")
def api_confluence():
    data = get_confluence()
    return jsonify(data)

# Serve frontend index.html
@app.route("/")
def serve_frontend():
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
