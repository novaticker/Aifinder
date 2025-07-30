import os
import json
import time
import joblib
import yfinance as yf
import pytz
import requests
import pandas as pd
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify, render_template
from flask_cors import CORS

# 기본 설정
KST = pytz.timezone('Asia/Seoul')
MODEL_PATH = "model.pkl"
SYMBOL_FILE = "symbols_nasdaq.json"
DATA_FILE = "ai_detected.json"
RENDER_URL = "https://aifinder-0bf3.onrender.com"
MAX_ENTRIES = 100

# 모델 로딩
model = joblib.load(MODEL_PATH)

# 심볼 로딩
SYMBOLS_CACHE = []
def load_symbols():
    global SYMBOLS_CACHE
    if SYMBOLS_CACHE:
        return SYMBOLS_CACHE
    if os.path.exists(SYMBOL_FILE):
        try:
            with open(SYMBOL_FILE, "r") as f:
                data = json.load(f)
                if data:
                    SYMBOLS_CACHE = data
                    return SYMBOLS_CACHE
        except:
            pass
    try:
        print("🔄 나스닥 전체 종목 자동 수집 중...")
        url = "https://old.nasdaq.com/screening/companies-by-name.aspx?exchange=NASDAQ&render=download"
        df = pd.read_csv(url)
        symbols = df["Symbol"].dropna().unique().tolist()
        SYMBOLS_CACHE = symbols[:1000]
        with open(SYMBOL_FILE, "w") as f:
            json.dump(SYMBOLS_CACHE, f, indent=2)
        return SYMBOLS_CACHE
    except Exception as e:
        print(f"❌ 종목 수집 실패: {e}")
        return []

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

# AI 판단
def is_ai_pick(df):
    if len(df) < 15:
        return False
    try:
        features = extract_features(df)
        return model.predict(features)[0] == 1
    except:
        return False

# 저장
def save_results(gainers, picks):
    now = datetime.now(KST)
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%Y-%m-%d")
    phase = get_market_phase()

    for item in gainers:
        item["time"] = time_str
        item["phase"] = phase
        item["date"] = date_str
    for item in picks:
        item["time"] = time_str
        item["phase"] = phase
        item["date"] = date_str

    data = {
        "time": time_str,
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
        if df.empty or len(df) < 15:
            return None
        info = yf.Ticker(symbol).info
        name = info.get("shortName", "")
        price = round(df["Close"].iloc[-1], 2)
        percent = df["Close"].pct_change().iloc[-1] * 100
        item = {
            "symbol": symbol,
            "name": name,
            "price": price,
            "percent": f"{percent:+.2f}%"
        }
        if is_ai_pick(df):
            item["summary"] = f"📈 AI 감지: {symbol}에 급등 신호 포착"
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
            result = scan_symbol(sym)
            if result:
                results.append(result)
                if result["ai_pick"]:
                    picks.append(result)

        for sym in symbols:
            t = Thread(target=worker, args=(sym,))
            t.start()
            threads.append(t)
            time.sleep(0.05)

        for t in threads:
            t.join()

        save_results(results, picks)
        time.sleep(60)

# 슬립 방지
def keep_alive():
    while True:
        try:
            requests.get(RENDER_URL + "/data.json")
        except:
            pass
        time.sleep(280)

# 웹 서버
app = Flask(__name__, template_folder="templates")
CORS(app)

@app.route("/data.json")
def data_json():
    today = datetime.now(KST).strftime("%Y-%m-%d")
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            gainers = [g for g in raw.get("gainers", []) if g.get("date") == today]
            picks = [p for p in raw.get("ai_picks", []) if p.get("date") == today]
            return jsonify({
                "gainers": gainers[-MAX_ENTRIES:],
                "ai_picks": picks[-MAX_ENTRIES:]
            })
    return jsonify({"gainers": [], "ai_picks": []})

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    Thread(target=run_loop, daemon=True).start()
    Thread(target=keep_alive, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
