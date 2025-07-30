# main.py
import os
import json
import time
import joblib
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
from threading import Thread
from flask import Flask, jsonify, render_template
from flask_cors import CORS
from symbols_manager import load_cached_symbols, fetch_and_cache_symbols

# 설정
KST = pytz.timezone('Asia/Seoul')
DATA_FILE = "detected_gainers.json"
MODEL_PATH = "models/model.pkl"

# Flask 앱 생성
app = Flask(__name__, template_folder="templates")
CORS(app)

# AI 모델 불러오기
model = joblib.load(MODEL_PATH)

# 시장 구분
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

# 급등 여부
def is_ai_gainer(df):
    if len(df) < 15:
        return False
    try:
        features = extract_features(df)
        return model.predict(features)[0] == 1
    except:
        return False

# 결과 저장
def save_detected(results):
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    now_time = datetime.now(KST).strftime("%H:%M")
    phase = get_market_phase()

    for r in results:
        if not any(d["symbol"] == r["symbol"] for d in data):
            r["time"] = now_time
            r["phase"] = phase
            r["summary"] = f"📈 AI 판단: {r['symbol']}에 급등 패턴 감지됨"
            data.append(r)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data[-100:], f, ensure_ascii=False, indent=2)

# 개별 종목 스캔
def scan_symbol(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if is_ai_gainer(df):
            price = round(df['Close'].iloc[-1], 2)
            ret = df["Close"].pct_change().iloc[-1] * 100
            return {
                "symbol": symbol,
                "price": price,
                "percent": f"{ret:+.2f}%"
            }
    except:
        return None

# 감지 루프
def run_detection_loop():
    symbols = load_cached_symbols()
    while True:
        results = []
        threads = []

        def worker(sym):
            result = scan_symbol(sym)
            if result:
                results.append(result)

        for sym in symbols:
            t = Thread(target=worker, args=(sym,))
            t.start()
            threads.append(t)
            time.sleep(0.05)  # 과부하 방지

        for t in threads:
            t.join()

        if results:
            save_detected(results)

        time.sleep(1)

# 앱 시작 시 스레드 시작
def start_detection_thread():
    t = Thread(target=run_detection_loop)
    t.daemon = True
    t.start()

start_detection_thread()  # 앱 실행 즉시 시작

# API: 감지 결과 반환
@app.route("/data.json")
def get_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify([])

# API: 종목 리스트 수동 갱신
@app.route("/update_symbols")
def update_symbols():
    symbols = fetch_and_cache_symbols()
    return jsonify({"status": "updated", "count": len(symbols)})

# 메인 페이지 렌더
@app.route("/")
def index():
    return render_template("index.html")

# 실행
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
