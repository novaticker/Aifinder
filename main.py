from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import os
import json
from datetime import datetime
from ai_model import is_ai_abnormal

app = Flask(__name__)
CORS(app)

DATA_FILE = 'ai_gainers.json'

def get_market_phase():
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    kst_hour = (hour + 9) % 24  # KST 기준
    kst_min = minute

    time_float = kst_hour + kst_min / 60

    if 9 <= time_float < 16.84:
        return '데이장'
    elif 17 <= time_float < 22.5:
        return '프리장'
    elif 22.5 <= time_float or time_float < 5:
        return '본장'
    elif 5 <= time_float < 8.84:
        return '애프터장'
    else:
        return '기타'

def scan_symbol(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if df is None or df.empty:
            return None
        if is_ai_abnormal(df):  # AI 판단
            price = round(df['Close'].iloc[-1], 2)
            percent = f"{df['Close'].pct_change().iloc[-1] * 100:+.2f}%"
            return {
                "symbol": symbol,
                "price": price,
                "percent": percent,
                "phase": get_market_phase()
            }
    except Exception as e:
        print(f"Error scanning {symbol}: {e}")
        return None

@app.route('/scan')
def scan():
    symbols = ['APLD', 'CYCC', 'LMFA', 'CW', 'SAIC']  # 예시 종목 리스트
    results = []

    for symbol in symbols:
        result = scan_symbol(symbol)
        if result:
            results.append(result)

    # 저장
    with open(DATA_FILE, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return jsonify(results)

@app.route('/gainers')
def gainers():
    if not os.path.exists(DATA_FILE):
        return jsonify([])

    with open(DATA_FILE, 'r') as f:
        data = json.load(f)

    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
