import requests, json, os, re, time, threading
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime
import pytz, websocket, traceback
from collections import deque
import numpy as np

app = Flask(__name__, template_folder="templates")
CORS(app)

KST = pytz.timezone("Asia/Seoul")
FINNHUB_TOKEN = "d1tic89r01qth6plf2kgd1tic89r01qth6plf2l0"
NEWS_FILE = "positive_news.json"
TICKER_FILE = "nasdaq_tickers.json"  # 전체 종목 리스트
MAX_HISTORY = 50  # 과거 데이터 저장 개수
Z_THRESHOLD = 3.0  # 급등 판단 기준 (Z-score)

price_history = {}  # {symbol: deque}
volume_history = {}  # {symbol: deque}
price_cache = {}     # 최근 가격 저장
WATCHLIST = []       # 전체 종목 로딩됨

# 🕒 장 구분
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
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    if os.path.exists(NEWS_FILE):
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    if today not in data:
        data[today] = {"gainers": []}
    existing = {g["symbol"] for g in data[today]["gainers"]}
    for g in gainers:
        if g["symbol"] not in existing:
            data[today]["gainers"].append(g)
    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 📌 실시간 감지 핸들러
def on_message(ws, message):
    try:
        msg = json.loads(message)
        if "data" not in msg: return
        now = datetime.now(KST)
        now_str = now.strftime("%H:%M")
        phase = get_market_phase()
        gainers = []

        for d in msg["data"]:
            s, p, v = d["s"], d["p"], d.get("v", 0)
            price_cache[s] = p

            # 가격 이력 누적
            if s not in price_history:
                price_history[s] = deque(maxlen=MAX_HISTORY)
            if s not in volume_history:
                volume_history[s] = deque(maxlen=MAX_HISTORY)
            price_history[s].append(p)
            volume_history[s].append(v)

            if len(price_history[s]) >= 10:
                # Z-score 계산
                price_array = np.array(price_history[s])
                price_mean = price_array.mean()
                price_std = price_array.std()
                z_price = (p - price_mean) / price_std if price_std > 0 else 0

                volume_array = np.array(volume_history[s])
                volume_mean = volume_array.mean()
                volume_std = volume_array.std()
                z_volume = (v - volume_mean) / volume_std if volume_std > 0 else 0

                # 급등 판단
                if z_price >= Z_THRESHOLD and z_volume >= Z_THRESHOLD:
                    percent_change = ((p - price_array[-2]) / price_array[-2]) * 100
                    gainers.append({
                        "symbol": s,
                        "price": round(p, 2),
                        "percent": f"{percent_change:+.2f}%",
                        "time": now_str,
                        "phase": phase
                    })

        if gainers:
            save_data(gainers)
            print(f"🚀 AI 급등 감지: {', '.join([g['symbol'] for g in gainers])}")
    except Exception as e:
        print("❌ message error:", e)
        traceback.print_exc()

def on_open(ws):
    print("🔗 WebSocket 연결됨")
    for symbol in WATCHLIST:
        ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))

def on_close(ws, *args):
    print("❌ 연결 종료됨. 재연결 시도 중...")
    time.sleep(3)
    start_websocket()

def on_error(ws, error):
    print("WebSocket Error:", error)

def start_websocket():
    url = f"wss://ws.finnhub.io?token={FINNHUB_TOKEN}"
    ws = websocket.WebSocketApp(url,
        on_open=on_open, on_message=on_message,
        on_close=on_close, on_error=on_error)
    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()

# 📌 전체 종목 불러오기
def load_watchlist():
    global WATCHLIST
    if os.path.exists(TICKER_FILE):
        with open(TICKER_FILE, "r") as f:
            WATCHLIST = json.load(f)
    else:
        print("❌ 나스닥 종목 리스트가 없습니다.")
        WATCHLIST = []

# ✅ Flask 라우트
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
    load_watchlist()
    start_websocket()
    app.run(host="0.0.0.0", port=10000)
