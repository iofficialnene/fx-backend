from flask import Flask, render_template, jsonify
from twelve import get_confluence  # your data function

app = Flask(__name__, template_folder="templates", static_folder="static")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/confluence")
def confluence_endpoint():
    try:
        data = get_confluence()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
