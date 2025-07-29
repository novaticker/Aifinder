# background_news_updater.py
import requests, json, os, re, random
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

NEWS_FILE = "positive_news.json"
KST = pytz.timezone("Asia/Seoul")

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
    elif any(k in text_lower for k in ["award", "event", "presentation", "expo"]):
        return combine("공식 발표 또는 수상 소식을 전달하며")
    elif any(k in text_lower for k in ["contract", "agreement", "deal", "signed"]):
        return combine("계약 또는 협약 체결을 발표하며")
    else:
        general = [
            "중요한 기업 활동을 발표하며",
            "새로운 전략을 제시하며",
            "시장과 투자자들에게 영향을 줄 수 있는 소식을 발표하며",
            "변화의 신호로 해석될 수 있는 뉴스를 전달하며"
        ]
        return combine(random.choice(general))

def clean_symbol(text):
    m = re.search(r"\(([A-Z]+)\)", text)
    return m.group(1) if m else ""

def fetch_toss_gainers():
    url = "https://tossinvest.com/screener"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")
    gainers = []
    for tag in soup.select("div > strong"):
        symbol = tag.text.strip()
        if len(symbol) <= 5 and symbol.isupper():
            gainers.append({"symbol": symbol})
    return gainers

def fetch_news_from_prnews():
    url = "https://www.prnewswire.com/news-releases/news-releases-list/"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")
    news_list = []

    for item in soup.select(".newsRelease"):
        title_tag = item.select_one(".newsTitle")
        if title_tag:
            title = title_tag.text.strip()
            link = "https://www.prnewswire.com" + title_tag.get("href")
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
    return news_list

def save_data(news, gainers):
    today = datetime.now(KST).strftime("%Y-%m-%d")
    if os.path.exists(NEWS_FILE):
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    data[today] = {
        "news": news,
        "gainers": gainers,
        "signals": []
    }
    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("🤖 진짜 AI 탐색기 작동 중...")
    gainers = fetch_toss_gainers()
    news = fetch_news_from_prnews()
    save_data(news, gainers)
    print("✅ 수집 및 분석 완료")

def update_news():
    main()

if __name__ == "__main__":
    main()
