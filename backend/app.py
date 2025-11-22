# backend/app.py
import os
import traceback
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from confluence import get_confluence

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")

app = Flask(
    __name__,
    static_folder=FRONTEND_DIST,
    static_url_path="/"
)

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}})

# -----------------------------------------------------
# GET CONFLUENCE DATA (MAIN API)
# -----------------------------------------------------
@app.route("/confluence")
def confluence_route():
    try:
        print("📊 Fetching confluence data...")
        data = get_confluence()
        
        if not data:
            print("⚠️ No data returned from get_confluence()")
            return jsonify({
                "error": "No confluence data returned",
                "data": []
            }), 500
        
        print(f"✅ Successfully fetched {len(data)} pairs")
        return jsonify(data)
        
    except Exception as e:
        print(f"❌ ERROR in /confluence: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "error": "Backend error in get_confluence",
            "detail": str(e),
            "trace": traceback.format_exc()
        }), 500

# -----------------