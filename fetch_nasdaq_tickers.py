import requests
import json

def fetch_nasdaq_tickers():
    url = "https://api.nasdaq.com/api/screener/stocks?exchange=nasdaq&download=true"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        tickers = [row["symbol"] for row in data["data"]["rows"] if row["symbol"].isalpha()]
        with open("nasdaq_tickers.json", "w") as f:
            json.dump(tickers, f, indent=2)
        print(f"✅ 총 {len(tickers)}개 나스닥 종목 저장 완료.")
    except Exception as e:
        print("❌ 나스닥 종목 수집 실패:", e)

if __name__ == "__main__":
    fetch_nasdaq_tickers()
