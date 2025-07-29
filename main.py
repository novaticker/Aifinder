import requests, json, os, re, time, threading
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime
import pytz
import websocket
import traceback
import numpy as np

app = Flask(__name__, template_folder="templates")
CORS(app)

NEWS_FILE = "positive_news.json"
KST = pytz.timezone("Asia/Seoul")
FINNHUB_TOKEN = "d1tic89r01qth6plf2kgd1tic89r01qth6plf2l0"

# 🔹 전체 감시 종목 로딩
with open("nasdaq_symbols.json", "r", encoding="utf-8") as f:
    WATCHLIST = json.load(f)[:1000]  # 성능상 일부 제한 가능 (전체 원하면 슬라이스 제거)

price_cache = {}
volume_cache = {}

# 📌 장 구분
def get_market_phase():
    now = datetime.now(KST)
    total = now.hour * 60 + now.minute
    if 540 <= total < 1010:
        return "day"
    elif 1020 <= total <= 1350:
        return "pre"
    elif total > 1350 or total < 300:
        return "normal"
    else:
        return "after"

# 📌 데이터 저장
def save_data(gainers):
    today = datetime.now(KST).strftime("%Y-%m-%d")
    if os.path.exists(NEWS_FILE):
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if today not in data:
        data[today] = {"news": [], "gainers": []}

    # 중복 제거 후 저장
    existing = {(g["symbol"], g["time"]) for g in data[today]["gainers"]}
    for g in gainers:
        key = (g["symbol"], g["time"])
        if key not in existing:
            data[today]["gainers"].append(g)

    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 📌 AI 급등 판단 기준 (z-score)
def is_ai_spike(symbol, price, volume):
    prices = price_cache.setdefault(symbol, [])
    volumes = volume_cache.setdefault(symbol, [])

    prices.append(price)
    volumes.append(volume)

    if len(prices) > 20:
        prices.pop(0)
    if len(volumes) > 20:
        volumes.pop(0)

    if len(prices) < 10:
        return False

    price_mean = np.mean(prices)
    price_std = np.std(prices)
    volume_mean = np.mean(volumes)
    volume_std = np.std(volumes)

    price_z = (price - price_mean) / price_std if price_std > 0 else 0
    volume_z = (volume - volume_mean) / volume_std if volume_std > 0 else 0

    return price_z > 2 and volume_z > 2  # 동시에 이상치일 때 급등으로 간주

# 📌 WebSocket 핸들링
def on_message(ws, message):
    try:
        msg = json.loads(message)
        if "data" not in msg:
            return

        now = datetime.now(KST)
        time_str = now.strftime("%H:%M")
        phase = get_market_phase()
        gainers = []

        for d in msg["data"]:
            s = d["s"]
            p = d["p"]
            v = d.get("v", 0)

            if is_ai_spike(s, p, v):
                gainers.append({
                    "symbol": s,
                    "price": p,
                    "volume": v,
                    "time": time_str,
                    "phase": phase
                })

        if gainers:
            save_data(gainers)
            print("🚀 급등 감지:", ", ".join([g["symbol"] for g in gainers]))

    except Exception as e:
        print("❌ WebSocket error:", e)
        traceback.print_exc()

def on_open(ws):
    print("🔗 WebSocket 연결됨")
    for s in WATCHLIST:
        ws.send(json.dumps({"type": "subscribe", "symbol": s}))

def on_close(ws, *args):
    print("🔌 WebSocket 끊김. 재연결 중...")
    time.sleep(3)
    start_websocket()

def on_error(ws, error):
    print("WebSocket 오류:", error)

def start_websocket():
    url = f"wss://ws.finnhub.io?token={FINNHUB_TOKEN}"
    ws = websocket.WebSocketApp(url,
        on_open=on_open,
        on_message=on_message,
        on_close=on_close,
        on_error=on_error)
    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()

# 📌 API
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data.json")
def get_data():
    if not os.path.exists(NEWS_FILE):
        return jsonify({})
    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))

# ▶️ 실행
if __name__ == "__main__":
    print("🚀 AI 급등 감지 시작")
    start_websocket()
    app.run(host="0.0.0.0", port=10000)
