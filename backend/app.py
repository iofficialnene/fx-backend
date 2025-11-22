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

# -----------------------------------------------------
# HEALTH CHECK
# -----------------------------------------------------
@app.route("/health")
def health():
    """Health check endpoint to verify backend is running"""
    frontend_exists = os.path.exists(FRONTEND_DIST)
    files = []
    
    if frontend_exists:
        try:
            files = os.listdir(FRONTEND_DIST)
        except Exception:
            files = ["error listing files"]
    
    return jsonify({
        "status": "ok",
        "port": str(os.environ.get("PORT", "5000")),
        "frontend_built": frontend_exists,
        "frontend_files": files[:10]  # First 10 files
    })

# -----------------------------------------------------
# SERVE FRONTEND (VITE/REACT)
# -----------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Serve the Vite-built React frontend from /frontend/dist"""
    
    # Check if frontend dist folder exists
    if not os.path.exists(FRONTEND_DIST):
        print(f"❌ Frontend dist folder not found at: {FRONTEND_DIST}")
        return jsonify({
            "error": "Frontend not built",
            "message": "The frontend/dist folder doesn't exist. Build failed during Docker build.",
            "expected_path": FRONTEND_DIST
        }), 500
    
    # If file exists in dist, serve it
    if path and os.path.exists(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)
    
    # Check if index.html exists
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if not os.path.exists(index_path):
        print(f"❌ index.html not found at: {index_path}")
        return jsonify({
            "error": "index.html not found",
            "message": "Frontend build incomplete",
            "dist_contents": os.listdir(FRONTEND_DIST) if os.path.exists(FRONTEND_DIST) else []
        }), 500
    
    # Otherwise serve index.html (SPA fallback)
    return send_from_directory(FRONTEND_DIST, "index.html")

# -----------------------------------------------------
# START
# -----------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting Flask app on port {port}")
    print(f"📁 Frontend dist path: {FRONTEND_DIST}")
    print(f"📁 Frontend dist exists: {os.path.exists(FRONTEND_DIST)}")
    
    if os.path.exists(FRONTEND_DIST):
        print(f"📁 Frontend files: {os.listdir(FRONTEND_DIST)[:5]}")
    
    app.run(host="0.0.0.0", port=port, debug=False)
```

---

# 📁 **File 3: Keep your requirements.txt** (already perfect!)

Your current requirements.txt is good - don't change it:
```
Flask==3.0.3
Flask-Cors==4.0.1
yfinance==0.2.40
pandas==2.2.3
numpy==1.26.4
gunicorn==21.2.0
requests==2.32.3
ratelimit==2.2.1
pytz==2024.1