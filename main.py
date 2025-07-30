from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import os
from ai_model import is_ai_abnormal

app = Flask(__name__)
CORS(app)

KST = pytz.timezone('Asia/Seoul')

@app.route('/check', methods=['POST'])
def check_stock():
    data = request.json
    symbol = data.get("symbol")

    if not symbol:
        return jsonify({"error": "symbol is required"}), 400

    try:
        df = fetch_stock_data(symbol)
        if df is None or len(df) < 10:
            return jsonify({"result": "no_data"})

        is_abnormal = is_ai_abnormal(df)
        return jsonify({"symbol": symbol, "ai_detected": is_abnormal})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def fetch_stock_data(symbol):
    try:
        now = datetime.now(KST)
        start = now - timedelta(days=3)

        df = yf.download(symbol, start=start.strftime('%Y-%m-%d'), interval='5m')
        if df.empty:
            return None
        df = df[['Close']].rename(columns={'Close': 'close'})
        return df
    except Exception as e:
        print(f"데이터 가져오기 오류: {e}")
        return None


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
