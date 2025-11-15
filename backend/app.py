from flask import Flask, render_template, jsonify
from twelve import get_confluence  # use your real function module

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/confluence")
def confluence_data():
    data = get_confluence()
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
