# trainer.py
import os
import json
import yfinance as yf
import pandas as pd
import joblib
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
import pytz

KST = pytz.timezone('Asia/Seoul')
MODEL_PATH = "models/model.pkl"
SYMBOL_FILE = "symbols_nasdaq.json"

def load_symbols():
    if os.path.exists(SYMBOL_FILE):
        with open(SYMBOL_FILE, "r") as f:
            return json.load(f)
    return []

def extract_features(df):
    df = df.copy()
    df["returns"] = df["Close"].pct_change()
    df["ma10"] = df["Close"].rolling(window=10).mean()
    df["ma_dev"] = (df["Close"] - df["ma10"]) / df["ma10"]
    df["volatility"] = df["returns"].rolling(window=10).std()
    df = df.dropna()
    return df[["returns", "ma_dev", "volatility"]]

def label_stock(df):
    # 전일 대비 종가 상승률이 10% 이상이면 1, 아니면 0
    try:
        change = (df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0]
        return 1 if change >= 0.10 else 0
    except:
        return 0

def train_model():
    symbols = load_symbols()
    X, y = [], []

    print(f"📊 학습 시작 - {len(symbols)} 종목")

    for symbol in symbols:
        try:
            df = yf.download(symbol, period="10d", interval="1d", progress=False)
            if df.empty or len(df) < 10:
                continue
            features = extract_features(df)
            if len(features) == 0:
                continue
            label = label_stock(df)
            X.append(features.iloc[-1].tolist())
            y.append(label)
        except Exception as e:
            continue

    if len(X) < 20:
        print("❌ 학습 데이터 부족")
        return

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)

    os.makedirs("models", exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"✅ 모델 저장 완료: {MODEL_PATH} ({len(X)}개 종목 학습)")

if __name__ == "__main__":
    train_model()
