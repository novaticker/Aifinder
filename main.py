# main.py
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import json
from datetime import datetime

app = Flask(__name__, template_folder="templates")
CORS(app)

NEWS_FILE = "positive_news.json"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data.json")
def get_data():
    today = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(NEWS_FILE):
        return jsonify({"news": [], "gainers": [], "signals": []})
    
    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return jsonify(data.get(today, {"news": [], "gainers": [], "signals": []}))

@app.route("/delete_news", methods=["POST"])
def delete_news():
    content = request.json
    title = content.get("title")
    symbol = content.get("symbol")
    today = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(NEWS_FILE):
        return jsonify({"status": "fail", "reason": "file not found"})

    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if today in data:
        before = len(data[today]["news"])
        data[today]["news"] = [
            item for item in data[today]["news"]
            if not (item.get("title") == title and item.get("symbol") == symbol)
        ]
        after = len(data[today]["news"])

        if after != before:
            with open(NEWS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "fail", "reason": "not found"})

    return jsonify({"status": "fail", "reason": "no data for today"})

@app.route("/update_news", methods=["POST"])
def update_news():
    os.system("python3 background_news_updater.py")
    return jsonify({"status": "updated"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
