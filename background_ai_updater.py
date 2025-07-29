import requests
import json
import os
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

KST = pytz.timezone("Asia/Seoul")
NEWS_FILE = "positive_news.json"

def get_today_date():
    return datetime.now(KST).strftime("%Y-%m-%d")

def true_ai_summarize(title):
    lowered = title.lower()
    if any(k in lowered for k in ['fda', 'clinical', 'phase']):
        return "FDA/임상 발표로 급등 가능성"
    if any(k in lowered for k in ['merger', 'acquisition']):
        return "인수합병 이슈로 상승 주목"
    if any(k in lowered for k in ['investment', 'funding']):
        return "투자 유치/지원 소식"
    if any(k in lowered for k in ['launch', 'release', 'expand']):
        return "신제품/서비스 출시 기대"
    if any(k in lowered for k in ['record', 'revenue', 'profit']):
        return "실적 관련 호재"
    return "긍정 뉴스 기반 상승 가능성"

def fetch_news_from_prnews():
    url = "https://www.prnewswire.com/news-releases/news-releases-list/?page=1&pagesize=100"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    items = soup.select("div.card")
    results = []
    for item in items:
        title_tag = item.select_one("a.card-title")
        time_tag = item.select_one("span.card-date")
        if not title_tag or not time_tag:
            continue
        title = title_tag.text.strip()
        link = "https://www.prnewswire.com" + title_tag.get("href", "")
        time_str = time_tag.text.strip()
        time_only = time_str.split(" ")[-1]
        symbol = extract_symbol(title)
        summary = true_ai_summarize(title)
        results.append({
            "title": title,
            "summary": summary,
            "link": link,
            "symbol": symbol,
            "time": time_only,
            "timestamp": int(datetime.now().timestamp()),
            "date": get_today_date(),
            "source": "PRNewswire"
        })
    return results

def extract_symbol(title):
    candidates = []
    words = title.split()
    for word in words:
        if word.isupper() and 1 <= len(word) <= 6 and word.isalpha():
            candidates.append(word)
    return candidates[0] if candidates else ""

def fetch_toss_gainers():
    url = "https://api.tossinvest.com/api-public/stock/us/stock-ranking/gainers"
    try:
        res = requests.get(url)
        items = res.json().get("data", {}).get("rankingStocks", [])
        result = []
        for item in items:
            result.append({
                "symbol": item.get("tickerSymbol", ""),
                "change": item.get("changeRate", ""),
                "phase": "프리장"  # 예시, 실제 구분 로직 필요 시 추가
            })
        return result
    except:
        return []

def save_data(news, gainers):
    if os.path.exists(NEWS_FILE):
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    today = get_today_date()
    data[today] = {
        "news": news,
        "gainers": gainers,
        "signals": []
    }

    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    news = fetch_news_from_prnews()
    gainers = fetch_toss_gainers()
    save_data(news, gainers)

if __name__ == "__main__":
    main()
