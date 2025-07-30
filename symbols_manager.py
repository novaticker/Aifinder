# symbols_manager.py
import os
import json
import requests

SYMBOLS_FILE = "nasdaq_symbols.json"

def fetch_and_cache_symbols():
    url = "https://api.nasdaq.com/api/screener/stocks?exchange=nasdaq&download=true"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        rows = data["data"]["rows"]
        symbols = [row["symbol"] for row in rows if row["symbol"].isalpha()]
        with open(SYMBOLS_FILE, "w", encoding="utf-8") as f:
            json.dump(symbols, f)
        return symbols
    except Exception as e:
        print("Error fetching symbols:", e)
        return []

def load_cached_symbols():
    if os.path.exists(SYMBOLS_FILE):
        with open(SYMBOLS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return fetch_and_cache_symbols()
