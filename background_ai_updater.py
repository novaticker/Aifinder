import requests, json, os, re
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

NEWS_FILE = "positive_news.json"
KST = pytz.timezone("Asia/Seoul")

def get_market_phase():
    now = datetime.now(KST)
    hour, minute = now.hour, now.minute
    total_minutes = hour * 60 + minute

    if 540 <= total_minutes < 1010:  # 09:00 ~ 16:50
        return "day"
    elif 1020 <= total_minutes <= 1350:  # 17:00 ~ 22:30
        return "pre"
    elif total_minutes > 1350 or total_minutes < 300:  # 22:30 ~ 05:00
        return "normal"
    else:  # 05:00 ~ 08:50
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

def parse_price(value):
    try:
        return float(value.replace("$", "").replace(",", ""))
    except:
        return None

def fetch_gainers_from_yahoo():
    try:
        url = "https://finance.yahoo.com/gainers"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        gainers = []
        now = datetime.now(KST).strftime("%H:%M")

        for row in soup.select("table tbody tr"):
            cols = row.find_all("td")
            if len(cols) >= 6:
                symbol = cols[0].text.strip()
                price = parse_price(cols[2].text.strip())
                percent = cols[4].text.strip()
                gainers.append({
                    "symbol": symbol,
                    "price": price,  # ✅ 숫자 형태로 저장
                    "percent": percent,
                    "time": now,
                    "phase": get_market_phase()
                })
        return gainers
    except Exception as e:
        print(f"❌ Yahoo Gainers Error: {e}")
        return []

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

    existing_titles = {n["title"] for n in data[today]["news"]}
    new_news = [n for n in news if n["title"] not in existing_titles]

    data[today]["news"].extend(new_news)
    data[today]["gainers"] = gainers

    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_news():
    print("🤖 AI 탐색기 수집 시작")
    gainers = fetch_gainers_from_yahoo()
    news = fetch_news_from_prnews()
    save_data(news, gainers)
    print("✅ 수집 완료")

if __name__ == "__main__":
    update_news()
