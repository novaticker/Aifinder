import requests, json, os, re, time, threading
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import websocket
import traceback

NEWS_FILE = "positive_news.json"
KST = pytz.timezone("Asia/Seoul")
FINNHUB_TOKEN = "d1tic89r01qth6plf2kgd1tic89r01qth6plf2l0"
WATCHLIST = ["NVDA", "TSLA", "AAPL", "AMZN", "AMD", "MARA", "RIOT", "AI", "BIDU", "PLTR"]

def get_market_phase():
    now = datetime.now(KST)
    hour, minute = now.hour, now.minute
    total_minutes = hour * 60 + minute
    if 540 <= total_minutes < 1010:
        return "day"
    elif 1020 <= total_minutes <= 1350:
        return "pre"
    elif total_minutes > 1350 or total_minutes < 300:
        return "normal"
    else:
        return "after"

def true_ai_summarize(text):
    text_lower = text.lower()
    symbol_match = re.search(r"\(([A-Z]+)\)", text)
    symbol = symbol_match.group(1) if symbol_match else ""
    company = symbol if symbol else "해당 기업"

    phrases = {
        "임상": ["fda", "approval", "phase", "clinical", "trial"],
        "인수합병": ["merger", "acquisition", "buyout"],
        "투자": ["investment", "funding", "raise", "partnership"],
        "제품출시": ["launch", "release", "expansion", "product", "platform"],
        "실적": ["earnings", "revenue", "record", "profit", "financial"]
    }

    reasons = {
        "임상": "긍정적인 임상 소식으로",
        "인수합병": "M&A 발표로",
        "투자": "투자유치 소식으로",
        "제품출시": "제품/서비스 출시로",
        "실적": "양호한 실적 발표로"
    }

    for key, keywords in phrases.items():
        if any(k in text_lower for k in keywords):
            return f"{company}는 {reasons[key]} 시장의 주목을 받고 있습니다."
    return f"{company}의 긍정적인 소식이 시장 반응을 이끌고 있습니다."

def clean_symbol(text):
    m = re.search(r"\(([A-Z]+)\)", text)
    return m.group(1) if m else ""

def fetch_news_from_prnews():
    news_list = []
    try:
        url = "https://www.prnewswire.com/news-releases/news-releases-list/"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        for item in soup.select(".newsRelease"):
            title_tag = item.select_one(".newsTitle")
            if not title_tag:
                continue
            title = title_tag.text.strip()
            link_tag = title_tag.get("href")
            if not link_tag:
                continue
            symbol = clean_symbol(title)
            if not symbol:
                continue

            link = "https://www.prnewswire.com" + link_tag
            summary = true_ai_summarize(title)
            now = datetime.now(KST)
            news_item = {
                "title": title,
                "link": link,
                "summary": summary,
                "symbol": symbol,
                "time": now.strftime("%H:%M"),
                "timestamp": now.timestamp(),
                "date": now.strftime("%Y-%m-%d"),
                "source": "PRNewswire"
            }
            news_list.append(news_item)
    except Exception as e:
        print(f"❌ PRNews fetch error: {e}")
    return news_list

def save_data(news, gainers):
    today = datetime.now(KST).strftime("%Y-%m-%d")
    if os.path.exists(NEWS_FILE):
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if today not in data:
        data[today] = {"news": [], "gainers": [], "signals": []}

    # 뉴스 중복 제거 후 추가
    existing_titles = {n["title"] for n in data[today]["news"]}
    new_news = [n for n in news if n["title"] not in existing_titles]
    data[today]["news"].extend(new_news)

    # gainers 실시간 반영
    symbols_in_today = {g["symbol"] for g in data[today]["gainers"]}
    for g in gainers:
        if g["symbol"] not in symbols_in_today:
            data[today]["gainers"].append(g)

    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ✅ 실시간 가격 수신 핸들러
price_cache = {}

def on_message(ws, message):
    try:
        msg = json.loads(message)
        if "data" not in msg:
            return
        now = datetime.now(KST).strftime("%H:%M")
        phase = get_market_phase()
        new_entries = []

        for item in msg["data"]:
            s = item["s"]
            p = item["p"]
            old_price = price_cache.get(s)

            # 가격 변화율 계산
            if old_price:
                change = (p - old_price) / old_price
                if abs(change) >= 0.03:  # 3% 이상 튀었을 때
                    percent_str = f"{change*100:+.2f}%"
                    new_entries.append({
                        "symbol": s,
                        "price": p,
                        "percent": percent_str,
                        "time": now,
                        "phase": phase
                    })
            price_cache[s] = p

        if new_entries:
            news = fetch_news_from_prnews()
            save_data(news, new_entries)
            print(f"🚀 급등 감지: {', '.join(e['symbol'] for e in new_entries)}")
    except Exception as e:
        print("❌ on_message error:", e)
        traceback.print_exc()

def on_error(ws, error):
    print("WebSocket Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("❌ WebSocket closed. Reconnecting in 5s...")
    time.sleep(5)
    start_websocket()  # 재연결

def on_open(ws):
    print("🔗 WebSocket 연결됨")
    for symbol in WATCHLIST:
        ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))

def start_websocket():
    url = f"wss://ws.finnhub.io?token={FINNHUB_TOKEN}"
    ws = websocket.WebSocketApp(url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close)
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()

def update_news():
    print("📡 초기 뉴스 수집 시작")
    news = fetch_news_from_prnews()
    save_data(news, [])
    print("✅ 초기 뉴스 수집 완료")

# ▶️ 실행 시작
if __name__ == "__main__":
    update_news()
    start_websocket()
    while True:
        time.sleep(30)
