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
        "frontend_files": files[:10]
    })

# -----------------------------------------------------
# TEST ENDPOINT
# -----------------------------------------------------
@app.route("/test")
def test_route():
    """Simple test to see if backend responds"""
    return jsonify({
        "status": "Backend is working!",
        "message": "If you see this, Flask is running fine",
        "timestamp": str(os.popen('date').read().strip())
    })

# -----------------------------------------------------
# DEBUG CONFLUENCE ENDPOINT
# -----------------------------------------------------
@app.route("/confluence-debug")
def confluence_debug():
    """Debug version that shows errors and first 2 results"""
    try:
        print("🔍 DEBUG: Starting confluence fetch...")
        data = get_confluence()
        print(f"🔍 DEBUG: Got {len(data) if data else 0} results")
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No data returned from get_confluence()",
                "count": 0,
                "data": []
            })
        
        return jsonify({
            "success": True,
            "count": len(data),
            "message": f"Successfully fetched {len(data)} pairs",
            "sample_data": data[:2]  # Only first 2 pairs for debugging
        })
        
    except Exception as e:
        print(f"❌ DEBUG ERROR: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500

# -----------------------------------------------------
# QUICK TEST - Single Pair
# -----------------------------------------------------
@app.route("/test-single")
def test_single():
    """Test fetching just one forex pair"""
    try:
        print("🧪 Testing single pair download...")
        import yfinance as yf
        
        # Try to download EUR/USD
        ticker = yf.Ticker("EURUSD=X")
        hist = ticker.history(period="5d")
        
        if hist.empty:
            return jsonify({
                "success": False,
                "error": "Yahoo Finance returned empty data",
                "ticker": "EURUSD=X"
            })
        
        return jsonify({
            "success": True,
            "ticker": "EURUSD=X",
            "rows": len(hist),
            "last_close": float(hist['Close'].iloc[-1]) if not hist.empty else None,
            "sample": hist.tail(2).to_dict()
        })
        
    except Exception as e:
        print(f"❌ Single test error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500

# -----------------------------------------------------
# SERVE FRONTEND (VITE/REACT)
# -----------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Serve the Vite-built React frontend from /frontend/dist"""
    
    if not os.path.exists(FRONTEND_DIST):
        print(f"❌ Frontend dist folder not found at: {FRONTEND_DIST}")
        return jsonify({
            "error": "Frontend not built",
            "message": "The frontend/dist folder doesn't exist. Build failed during Docker build.",
            "expected_path": FRONTEND_DIST
        }), 500
    
    if path and os.path.exists(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)
    
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if not os.path.exists(index_path):
        print(f"❌ index.html not found at: {index_path}")
        return jsonify({
            "error": "index.html not found",
            "message": "Frontend build incomplete",
            "dist_contents": os.listdir(FRONTEND_DIST) if os.path.exists(FRONTEND_DIST) else []
        }), 500
    
    return send_from_directory(FRONTEND_DIST, "index.html")

# -----------------------------------------------------
# START
# -----------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting Flask app on port {port}")
    print(f"📁 Frontend dist path: {FRONTEND_DIST}")
    print(f"📁 Frontend dist