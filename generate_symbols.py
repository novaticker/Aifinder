import requests
import json

def fetch_nasdaq_symbols():
    url = "https://api.nasdaq.com/api/screener/stocks?exchange=nasdaq&download=true"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    rows = data["data"]["rows"]
    symbols = [row["symbol"] for row in rows if row.get("symbol")]
    return symbols

if __name__ == "__main__":
    symbols = fetch_nasdaq_symbols()
    with open("symbols_nasdaq.json", "w") as f:
        json.dump(symbols, f, indent=2)
    print(f"✅ 저장 완료: {len(symbols)}개 종목 -> symbols_nasdaq.json")
