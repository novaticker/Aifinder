import os
import json
import time
import joblib
import yfinance as yf
import pytz
import requests
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify, render_template
from flask_cors import CORS

# 설정
KST = pytz.timezone('Asia/Seoul')
MODEL_PATH = "model.pkl"
DATA_FILE = "ai_detected.json"
RENDER_URL = "https://aifinder-0bf3.onrender.com"
MAX_ENTRIES = 100

# 모델 로딩
model = joblib.load(MODEL_PATH)

# 종목 리스트 캐시 (한 번만 로드)
SYMBOLS_CACHE = []
def load_symbols():
    global SYMBOLS_CACHE
    if not SYMBOLS_CACHE:
        with open("symbols_nasdaq.json", "r") as f:
            SYMBOLS_CACHE = json.load(f)
    return SYMBOLS_CACHE

# 장 구분
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

# 피처 추출
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

# AI 감지
def is_ai_gainer(df):
    if len(df) < 15:
        return False
    try:
        features = extract_features(df)
        return model.predict(features)[0] == 1
    except:
        return False

# 저장
def save_results(gainers, picks):
    now = datetime.now(KST).strftime("%H:%M")
    phase = get_market_phase()

    data = {
        "time": now,
        "phase": phase,
        "gainers": gainers[-MAX_ENTRIES:],
        "ai_picks": picks[-MAX_ENTRIES:]
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 종목 분석
def scan_symbol(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        info = yf.Ticker(symbol).info
        name = info.get("shortName", "")
        price = round(df["Close"].iloc[-1], 2)
        percent = df["Close"].pct_change().iloc[-1] * 100

        item = {
            "symbol": symbol,
            "name": name,
            "price": price,
            "percent": f"{percent:+.2f}%",
            "time": datetime.now(KST).strftime("%H:%M"),
            "phase": get_market_phase()
        }

        if is_ai_gainer(df):
            item["summary"] = f"📈 AI 감지: {symbol} 급등 신호 포착"
            item["ai_pick"] = True
        else:
            item["ai_pick"] = False

        return item
    except:
        return None

# 감지 루프
def run_loop():
    symbols = load_symbols()
    while True:
        results = []
        picks = []
        threads = []

        def worker(sym):
            res = scan_symbol(sym)
            if res:
                results.append(res)
                if res["ai_pick"]:
                    picks.append(res)

        for s in symbols:
            t = Thread(target=worker, args=(s,))
            t.start()
            threads.append(t)
            time.sleep(0.05)

        for t in threads:
            t.join()

        save_results(results, picks)
        time.sleep(60)

# 렌더 슬립 방지
def keep_alive():
    while True:
        try:
            requests.get(RENDER_URL)
        except:
            pass
        time.sleep(300)

# Flask 웹 서버
app = Flask(__name__, template_folder="templates")
CORS(app)

@app.route("/data.json")
def data_json():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"gainers": [], "ai_picks": []})

@app.route("/")
def index():
    return render_template("index.html")

# 시작
if __name__ == "__main__":
    Thread(target=run_loop, daemon=True).start()
    Thread(target=keep_alive, daemon=True).start()
    app.run(debug=False, host="0.0.0.0", port=5000)
