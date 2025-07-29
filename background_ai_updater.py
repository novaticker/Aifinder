import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import json
import re

KST = pytz.timezone("Asia/Seoul")
NEWS_FILE = "positive_news.json"

# 📊 프장 / 📈 본장 / 🌙 앱장 구분
def get_phase_now():
    now = datetime.now(KST).time()
    if now < datetime.strptime("22:30", "%H:%M").time():
        return "📊 프장"
    elif now < datetime.strptime("05:00", "%H:%M").time():
        return "📈 본장"
    else:
        return "🌙 앱장"

# 가짜 AI 요약 생성기
def true_ai_summarize(title):
    text = title.lower()
    if any(k in text for k in ["fda", "approval", "clinical", "phase"]):
        return "임상/승인 관련 발표로 기대감 상승"
    if any(k in text for k in ["merger", "acquisition", "buyout"]):
        return "M&A 관련 소식으로 투자자 관심 집중"
    if any(k in text for k in ["investment", "funding", "raises", "capital"]):
        return "투자유치 또는 자금 조달 발표"
    if any(k in text for k in ["launch", "expand", "partnership", "open"]):
        return "신제품 출시, 확장 또는 제휴 발표"
    if any(k in text for k in ["record", "surge", "strong", "beat"]):
        return "실적 호조 또는 성장 기록 발표"
    return "긍정적인 기업 발표로 주목"

# 심볼 추출 (대문자 연속)
def extract_symbol(text):
    matches = re.findall(r"\b[A-Z]{2,5}\b", text)
    if matches:
        return matches[0]
    return ""

# PR Newswire 크롤링
def fetch_news_from_prnews():
    url = "https://www.prnewswire.com/news-releases/news-releases-list/"
    res = requests.get(url, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    items = soup.select(".card")
    results = []
    for item in items:
        title_tag = item.select_one(".news-release .card-title")
        if not title_tag:
            continue
        title = title_tag.text.strip()
        link = "https://www.prnewswire.com" + title_tag.get("href", "")
        symbol = extract_symbol(title)
        summary = true_ai_summarize(title)
        time_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
        source = "PRNewswire"
        results.append({
            "title": title,
            "summary": summary,
            "link": link,
            "symbol": symbol,
            "time": time_str,
            "timestamp": datetime.now(KST).timestamp(),
            "date": datetime.now(KST).strftime("%Y-%m-%d"),
            "source": source
        })
    return results

# TossInvest 급등 종목 감지
def fetch_toss_gainers():
    try:
        url = "https://www.tossinvest.com/api/statics/today-top-rising-stocks"
        res = requests.get(url, timeout=10)
        data = res.json().get("data", [])
        phase = get_phase_now()
        gainers = []
        for item in data:
            symbol = item.get("symbol", "")
            change = item.get("changeRate", "")
            gainers.append({
                "symbol": symbol,
                "change": change,
                "phase": phase
            })
        return gainers
    except:
        return []

# 데이터 저장
def save_data(news_items, gainers):
    date = datetime.now(KST).strftime("%Y-%m-%d")
    if not news_items and not gainers:
        return

    if not os.path.exists(NEWS_FILE):
        data = {}
    else:
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    if date not in data:
        data[date] = {"news": [], "gainers": []}

    # 뉴스 중복 제거 (제목 기준)
    existing_titles = {item["title"] for item in data[date]["news"]}
    new_news = [item for item in news_items if item["title"] not in existing_titles]
    data[date]["news"].extend(new_news)

    # 급등 종목 최신화
    data[date]["gainers"] = gainers

    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 외부에서 호출할 함수
def update_news():
    news = fetch_news_from_prnews()
    gainers = fetch_toss_gainers()
    save_data(news, gainers)

# 수동 실행용
if __name__ == "__main__":
    update_news()
