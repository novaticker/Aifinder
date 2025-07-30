# generate_symbols.py
import requests
import json

def get_nasdaq_symbols():
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&exchange=nasdaq"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)
    data = response.json()

    symbols = []
    rows = data["data"]["table"]["rows"]
    for row in rows:
        symbol = row["symbol"]
        if symbol.isalpha():  # 숫자/우선주 제외
            symbols.append(symbol)

    return symbols

def save_symbols(symbols, filename="symbols_nasdaq.json"):
    with open(filename, "w") as f:
        json.dump(symbols, f, indent=2)

if __name__ == "__main__":
    symbols = get_nasdaq_symbols()
    save_symbols(symbols)
    print(f"{len(symbols)} symbols saved to symbols_nasdaq.json")
