# main.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json
import background_ai_updater  # 같은 폴더에 있어야 함

app = Flask(__name__)
CORS(app)

NEWS_FILE = "positive_news.json"

@app.route("/")
def home():
    return "✅ NovaTicker AI Finder is running."

@app.route("/data.json")
def get_all_data():
    if not os.path.exists(NEWS_FILE):
        return jsonify({})
    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

@app.route("/update_news")
def trigger_update():
    try:
        background_ai_updater.update_news()
        return "✅ News updated successfully."
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route("/delete_news", methods=["POST"])
def delete_news():
    try:
        symbol = request.json.get("symbol")
        title = request.json.get("title")
        date = request.json.get("date")

        if not all([symbol, title, date]):
            return jsonify({"status": "error", "message": "Missing parameters"})

        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if date in data and "news" in data[date]:
            original = len(data[date]["news"])
            data[date]["news"] = [
                item for item in data[date]["news"]
                if not (item.get("symbol") == symbol and item.get("title") == title)
            ]
            if len(data[date]["news"]) < original:
                with open(NEWS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return jsonify({"status": "success"})
            else:
                return jsonify({"status": "error", "message": "Item not found"})
        else:
            return jsonify({"status": "error", "message": "Date not found"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
