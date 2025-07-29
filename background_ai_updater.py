import requests, json, os, re, random
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

NEWS_FILE = "positive_news.json"
KST = pytz.timezone("Asia/Seoul")

def get_market_phase():
    hour = datetime.now(KST).hour
    if hour < 22:
        return "프리장"
    elif 22 <= hour <= 28:
        return "본장"
    else:
        return "애프터장"

def true_ai_summarize(text):
    text_lower = text.lower()
    symbol_match = re.search(r"\(([A-Z]+)\)", text)
    symbol = symbol_match.group(1) if symbol_match else ""
    company = symbol if symbol else "해당 기업"

    positive_adverbs = ["긍정적인", "고무적인", "희망적인", "주목할 만한", "활발한"]
    market_reactions = [
        "시장 반응을 이끌 것으로 예상됩니다.",
        "투자 심리에 영향을 줄 수 있습니다.",
        "주가 변동에 중요한 요소로 작용할 수 있습니다.",
        "향후 성장 기대감을 키우고 있습니다.",
        "중장기 관점에서 주목받고 있습니다."
    ]

    def combine(phrase):
        return f"{company}는 {phrase} {random.choice(market_reactions)}"

    if any(k in text_lower for k in ["fda", "approval", "phase", "clinical", "trial"]):
        return combine(f"{random.choice(positive_adverbs)} 임상 또는 승인 관련 소식을 발표하며")
    elif any(k in text_lower for k in ["merger", "acquisition", "buyout"]):
        return combine("인수합병(M&A) 관련 발표를 통해")
    elif any(k in text_lower for k in ["investment", "funding", "raise", "partnership"]):
        amt = re.search(r"(\$[0-9,.]+[MB]?)", text)
        amount = amt.group(1) if amt else "자금"
        return combine(f"{amount} 규모의 투자 또는 제휴를 진행하며")
    elif any(k in text_lower for k in ["launch", "release", "expansion", "product", "platform"]):
        return combine("신제품 또는 플랫폼 확장을 발표하며")
    elif any(k in text_lower for k in ["earnings", "revenue", "record", "profit", "%", "financial"]):
        return combine("재무 수치 또는 실적 발표를 통해")
    else:
        return combine("중요 발표를 하며")

def clean_symbol(text):
    m = re.search(r"\(([A-Z]+)\)", text)
    return m.group(1) if m else ""

def fetch_gainers_from_yahoo():
    try:
        url = "https://finance.yahoo.com/gainers"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        gainers = []
        for row in soup.select("table tbody tr"):
            cols = row.find_all("td")
            if len(cols) >= 3:
                symbol = cols[0].text.strip()
                change = cols[2].text.strip()
                gainers.append({
                    "symbol": symbol,
                    "change": change,
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
            link = "https://www.prnewswire.com" + link_tag
            summary = true_ai_summarize(title)
            symbol = clean_symbol(title)
            now = datetime.now(KST)
            news_list.append({
                "title": title,
                "link": link,
                "summary": summary,
                "symbol": symbol,
                "time": now.strftime("%H:%M"),
                "timestamp": now.timestamp(),
                "date": now.strftime("%Y-%m-%d"),
                "source": "PRNewswire"
            })
    except Exception as e:
        print(f"❌ PRNews fetch error: {e}")
    return news_list

def save_data(news, gainers):
    today = datetime.now(KST).strftime("%Y-%m-%d")
    data = {}  # ✅ 기존 파일 덮어쓰기 방식으로 변경
    data[today] = {
        "news": news,
        "gainers": gainers,
        "signals": []
    }
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
