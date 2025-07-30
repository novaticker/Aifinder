import yfinance as yf
import pandas as pd
import time, json, os
from datetime import datetime
import pytz
from threading import Thread

KST = pytz.timezone('Asia/Seoul')
DATA_FILE = "detected_gainers.json"

def get_market_phase():
    now = datetime.now(KST)
    t = now.hour * 60 + now.minute
    if 540 <= t < 1010: return "day"
    elif 1020 <= t <= 1350: return "pre"
    elif t > 1350 or t < 300: return "normal"
    else: return "after"

def is_ai_abnormal(df):
    if len(df) < 15:
        return False

    df['returns'] = df['Close'].pct_change()
    df['ma'] = df['Close'].rolling(window=10).mean()
    df['ma_dev'] = (df['Close'] - df['ma']) / df['ma']

    z = (df['returns'].iloc[-1] - df['returns'].mean()) / (df['returns'].std() + 1e-9)
    dev = df['ma_dev'].iloc[-1]
    vol = df['returns'].std()

    # AI 판단 로직: 학습된 기준처럼 종합 판단
    if z > 2.8 and dev > 0.05 and vol > 0.01:
        return True
    return False

def load_nasdaq():
    url = "https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download"
    df = pd.read_csv(url)
    return df['Symbol'].dropna().tolist()[:1000]  # 상위 1000개 제한

def save_detected(gainers):
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    now_time = datetime.now(KST).strftime("%H:%M")
    phase = get_market_phase()

    for g in gainers:
        if not any(d['symbol'] == g['symbol'] for d in data):
            g['time'] = now_time
            g['phase'] = phase
            g['summary'] = f"📈 AI 판단: {g['symbol']}에 급등 패턴 감지됨"
            data.append(g)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data[-100:], f, ensure_ascii=False, indent=2)

def scan_symbol(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if is_ai_abnormal(df):
            price = round(df['Close'].iloc[-1], 2)
            percent = f"{df['returns'].iloc[-1] * 100:+.2f}%"
            return {
                "symbol": symbol,
                "price": price,
                "percent": percent
            }
    except:
        return None

def main_ai_loop():
    symbols = load_nasdaq()
    while True:
        detected = []

        threads = []
        results = []

        def worker(sym):
            result = scan_symbol(sym)
            if result:
                results.append(result)

        for sym in symbols:
            t = Thread(target=worker, args=(sym,))
            threads.append(t)
            t.start()
            time.sleep(0.05)  # 서버 과부하 방지

        for t in threads:
            t.join()

        if results:
            save_detected(results)

        time.sleep(1)

if __name__ == "__main__":
    main_ai_loop()
