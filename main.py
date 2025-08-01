import os
import json
import time
import joblib
import yfinance as yf
import pytz
import requests
import pandas as pd
import subprocess
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify, render_template
from flask_cors import CORS

KST = pytz.timezone('Asia/Seoul')
MODEL_PATH = "models/model.pkl"
SYMBOL_FILE = "symbols_nasdaq.json"
DATA_FILE = "ai_detected.json"
RENDER_URL = "https://aifinder-0bf3.onrender.com"
MAX_ENTRIES = 100

model = joblib.load(MODEL_PATH)
SYMBOLS_CACHE = []

def load_symbols():
    global SYMBOLS_CACHE
    if SYMBOLS_CACHE:
        return SYMBOLS_CACHE
    try:
        if os.path.exists(SYMBOL_FILE):
            with open(SYMBOL_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    SYMBOLS_CACHE = data
                    return SYMBOLS_CACHE
        print("🔄 나스닥 종목 수집 중...")

        url = "https://old.nasdaq.com/screening/companies-by-name.aspx?exchange=NASDAQ&render=download"
        df = pd.read_csv(url)
        symbols = df["Symbol"].dropna().unique().tolist()

        filtered = []
        blocklist = ["AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "META", "TSLA"]

        for symbol in symbols:
            if symbol in blocklist:
                continue
            try:
                info = yf.Ticker(symbol).info
                price = info.get("regularMarketPrice", 0)
                cap = info.get("marketCap", 0)
                vol = info.get("averageVolume", 0)

                if price and 0.5 <= price <= 500 and cap < 5e9 and vol >= 100000:
                    hist = yf.download(symbol, period="10d", interval="1d", progress=False)
                    if len(hist) >= 2:
                        change = (hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0]
                        if abs(change) >= 0.10:
                            filtered.append(symbol)
                if len(filtered) >= 800:
                    break
            except:
                continue

        SYMBOLS_CACHE = filtered
        with open(SYMBOL_FILE, "w") as f:
            json.dump(filtered, f, indent=2)
        print(f"✅ 필터링 완료: {len(filtered)}개 종목 저장됨")
        return filtered
    except Exception as e:
        print(f"❌ 종목 수집 실패: {e}")
        return []

def get_market_phase():
    now = datetime.now(KST)
    t = now.hour * 60 + now.minute
    if 540 <= t < 1010:
        return "day"
    elif 1020 <= t < 1350:
        return "pre"
    elif 1350 <= t or t < 300:
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

def is_ai_pick(df):
    if len(df) < 15:
        return False
    try:
        features = extract_features(df)
        return model.predict(features)[0] == 1
    except:
        return False

def save_results(gainers, picks):
    now = datetime.now(KST)
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%Y-%m-%d")
    phase = get_market_phase()

    for item in gainers + picks:
        item["time"] = time_str
        item["date"] = date_str
        item["phase"] = phase

    data = {
        "time": time_str,
        "phase": phase,
        "gainers": gainers[-MAX_ENTRIES:],
        "ai_picks": picks[-MAX_ENTRIES:]
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def reset_data_daily():
    while True:
        now = datetime.now(KST)
        if now.strftime("%H:%M") == "05:10":
            print("🧹 데이터 초기화")
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({"gainers": [], "ai_picks": []}, f)
        time.sleep(60)

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

def run_loop():
    symbols = load_symbols()
    while True:
        results, picks, threads = [], [], []

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

def keep_alive():
    while True:
        try:
            requests.get(RENDER_URL + "/data.json")
        except:
            pass
        time.sleep(280)

app = Flask(__name__, template_folder="templates")
CORS(app)

@app.route("/data.json")
def data_json():
    today = datetime.now(KST).strftime("%Y-%m-%d")
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            gainers = [x for x in raw.get("gainers", []) if x.get("date") == today]
            picks = [x for x in raw.get("ai_picks", []) if x.get("date") == today]
            return jsonify({
                "gainers": gainers[-MAX_ENTRIES:],
                "ai_picks": picks[-MAX_ENTRIES:]
            })
    return jsonify({"gainers": [], "ai_picks": []})

@app.route("/train_model")
def train_model():
    try:
        result = subprocess.run(["python3", "trainer.py"], capture_output=True, text=True)
        return f"<pre>{result.stdout}</pre>"
    except Exception as e:
        return f"Training failed: {e}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ping")
def ping():
    return "pong"

if __name__ == "__main__":
    Thread(target=run_loop, daemon=True).start()
    Thread(target=keep_alive, daemon=True).start()
    Thread(target=reset_data_daily, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
