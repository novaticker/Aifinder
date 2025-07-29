import requests
import csv

def fetch_nasdaq_tickers():
    url = "https://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
    response = requests.get(url)
    lines = response.text.strip().split('\n')

    tickers = []
    for line in csv.reader(lines[1:], delimiter='|'):
        symbol = line[0]
        if symbol and symbol != 'File Creation Time':
            tickers.append(symbol)

    # 저장
    with open("nasdaq_symbols.json", "w", encoding="utf-8") as f:
        import json
        json.dump(tickers, f, ensure_ascii=False, indent=2)

    print(f"✅ 총 {len(tickers)}개 나스닥 종목 저장 완료")

if __name__ == "__main__":
    fetch_nasdaq_tickers()
