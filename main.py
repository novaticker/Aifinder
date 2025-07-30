import os
import json
import time
import joblib
import yfinance as yf
import pandas as pd
import pytz
import requests
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify, render_template
from flask_cors import CORS
from symbols_manager import load_cached_symbols, fetch_and_cache_symbols

# 설정
KST = pytz.timezone("Asia/Seoul")
DATA_FILE = "detected_gainers.json"
RECOMMEND_FILE = "ai_picks.json"
MODEL_PATH = "models/model.pkl"
RENDER_URL = "https://aifinder-0bf3.onrender.com"

app = Flask(__name__, template_folder="templates")
CORS(app)

model = joblib.load(MODEL_PATH)

def get_market_phase():
    now = datetime.now(KST)
    t = now.hour * 60 + now.minute
    if 540 <= t < 1010:
        return "day"
    elif 1020 <= t <= 1350:
        return "pre"
    elif t > 1350 or t < 300:
        return "normal"
    else:
        return "after"

def extract_features(df):
    df = df.copy()
    df["returns"] = df["Close"].pct_change()
    df["ma10"] = df["Close"].rolling(window=10).mean()
    df["ma_dev"] = (df["Close"] - df["ma10"]) / df["ma10"]
    df["volatility"] = df["returns"].rolling(window=10).std()
    latest = df.iloc[-1]
    return [[
        latest["returns"],
        latest["ma_dev"],
        latest["volatility"]
    ]]

def is_ai_gainer(df):
    if len(df) < 15:
        return False
    try:
        features = extract_features(df)
        return model.predict(features)[0] == 1
    except:
        return False

def save_detected(results):
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"ai_picks": [], "gainers": []}, f)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    now_time = datetime.now(KST).strftime("%H:%M")
    phase = get_market_phase()

    for r in results:
        r["time"] = now_time
        r["phase"] = phase
        r["summary"] = f"📈 AI 판단: {r['symbol']}에 급등 패턴 감지됨"

        if r.get("ai_pick"):
            if not any(d["symbol"] == r["symbol"] for d in data["ai_picks"]):
                data["ai_picks"].append(r)
        else:
            if not any(d["symbol"] == r["symbol"] for d in data["gainers"]):
                data["gainers"].append(r)

    data["ai_picks"] = data["ai_picks"][-100:]
    data["gainers"] = data["gainers"][-100:]

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_ai_recommendations(recommendations):
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    for r in recommendations:
        r["summary"] = f"📌 AI 추천: {r['symbol']}은 추가 상승 여지가 있습니다."
        r["time"] = now

    with open(RECOMMEND_FILE, "w", encoding="utf-8") as f:
        json.dump({"ai_picks": recommendations}, f, ensure_ascii=False, indent=2)

def scan_symbol(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        info = yf.Ticker(symbol).info
        name = info.get("shortName", "")
        price = round(df['Close'].iloc[-1], 2)
        ret = df["Close"].pct_change().iloc[-1] * 100

        item = {
            "symbol": symbol,
            "name": name,
            "price": price,
            "percent": f"{ret:+.2f}%"
        }

        item["ai_pick"] = is_ai_gainer(df)
        return item, df
    except:
        return None, None

def run_detection_loop():
    symbols = load_cached_symbols()
    while True:
        results = []
        threads = []
        ai_recommend = []

        def worker(sym):
            result, df = scan_symbol(sym)
            if result:
                results.append(result)
                if is_ai_gainer(df):
                    ai_recommend.append(result)

        for sym in symbols:
            t = Thread(target=worker, args=(sym,))
            t.start()
            threads.append(t)
            time.sleep(0.05)

        for t in threads:
            t.join()

        if results:
            save_detected(results)

        if ai_recommend:
            save_ai_recommendations(ai_recommend)

        time.sleep(60)

def keep_alive_loop():
    while True:
        try:
            requests.get(RENDER_URL)
        except Exception as e:
            print(f"[Ping 실패] {e}")
        time.sleep(300)

def start_detection_thread():
    t = Thread(target=run_detection_loop)
    t.daemon = True
    t.start()

def start_keep_alive_thread():
    t = Thread(target=keep_alive_loop)
    t.daemon = True
    t.start()

start_detection_thread()
start_keep_alive_thread()

@app.route("/data.json")
def get_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"ai_picks": [], "gainers": []})

@app.route("/ai.json")
def get_ai_data():
    if os.path.exists(RECOMMEND_FILE):
        with open(RECOMMEND_FILE, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"ai_picks": []})

@app.route("/update_symbols")
def update_symbols():
    symbols = fetch_and_cache_symbols()
    return jsonify({"status": "updated", "count": len(symbols)})

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
