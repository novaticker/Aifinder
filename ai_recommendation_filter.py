import json
import requests
import pickle
from datetime import datetime
import pytz

# AI 모델 불러오기
with open("model.pkl", "rb") as f:
    model = pickle.load(f)

# 한국 시간 기준
KST = pytz.timezone("Asia/Seoul")
now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

# TossInvest 급등 종목 긁어오기 (예시, 실제로는 크롤링 또는 API 필요)
def fetch_top_movers():
    # 여긴 실제 종목 리스트 수집하는 코드가 들어가야 함
    return [
        {"symbol": "EVLO", "price": 0.21, "change_percent": 43.3, "volume": 5320000},
        {"symbol": "ACON", "price": 1.11, "change_percent": 27.0, "volume": 3200000},
        # ...
    ]

# AI 추천 필터
def ai_filter(stocks):
    selected = []
    for stock in stocks:
        features = [
            stock["price"],
            stock["change_percent"],
            stock["volume"]
        ]
        try:
            prediction = model.predict([features])
            if prediction[0] == 1:  # 더 상승할 종목
                stock["time"] = now
                selected.append(stock)
        except Exception as e:
            print(f"모델 예측 오류: {e}")
    return selected

# 저장
def save_recommendations(data):
    try:
        with open("ai_picks.json", "w", encoding="utf-8") as f:
            json.dump({"ai_picks": data}, f, ensure_ascii=False, indent=2)
        print(f"[{now}] AI 추천 저장 완료 - {len(data)}개 종목")
    except Exception as e:
        print(f"저장 실패: {e}")

def main():
    print(f"[{now}] AI 추천 실행 중...")
    stocks = fetch_top_movers()
    recommended = ai_filter(stocks)
    save_recommendations(recommended)

if __name__ == "__main__":
    main()
