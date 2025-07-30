import numpy as np
import pandas as pd
import joblib
import os

# 모델 불러오기 (최초 1회)
MODEL_PATH = os.path.join("models", "model.pkl")
model = joblib.load(MODEL_PATH)

def is_ai_abnormal(df):
    """
    df: DataFrame, 최소 10개의 가격 정보 필요 (시간순 정렬)
    """
    df["returns"] = df["close"].pct_change()
    df = df.dropna()

    # AI 입력 특징 추출 (예: z-score, 평균편차, 변동성 등)
    z = (df["close"].iloc[-1] - df["close"].mean()) / df["close"].std()
    dev = np.abs(df["close"] - df["close"].rolling(5).mean()).mean()
    vol = df["returns"].std()

    features = np.array([[z, dev, vol]])
    pred = model.predict(features)

    return pred[0] == 1
