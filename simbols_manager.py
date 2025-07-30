# symbols_manager.py
import pandas as pd
import json
import os

CACHE_FILE = "nasdaq_cache.json"
CSV_URL = "https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download"

def fetch_and_cache_symbols():
    try:
        df = pd.read_csv(CSV_URL)
        symbols = df["Symbol"].dropna().tolist()
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(symbols, f)
        return symbols
    except:
        return load_cached_symbols()

def load_cached_symbols():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return fetch_and_cache_symbols()
