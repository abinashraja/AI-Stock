"""
SKILL: News & Sentiment
Fetches latest news from yfinance and Google News RSS.
Source: yfinance news + Google News RSS (free)
"""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime


def get_news(stock, company_name: str) -> dict:
    headlines = []

    # ── Source 1: yfinance news ───────────────────────────────────────────────
    try:
        for item in (stock.news or [])[:8]:
            title = item.get("title", "")
            pub   = item.get("providerPublishTime", 0)
            src   = item.get("publisher", "")
            link  = item.get("link", "")
            if title:
                ts = datetime.fromtimestamp(pub).strftime("%Y-%m-%d") if pub else "N/A"
                headlines.append({"title": title, "date": ts, "source": src, "url": link})
    except:
        pass

    # ── Source 2: Google News RSS ─────────────────────────────────────────────
    try:
        query = company_name.replace(" ", "+") + "+stock+India"
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        resp = requests.get(rss_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:6]:
                title   = item.findtext("title", "")
                pub_raw = item.findtext("pubDate", "")
                link    = item.findtext("link", "")
                source  = item.findtext("source", "Google News")
                if title:
                    try:
                        ts = datetime.strptime(pub_raw[:16], "%a, %d %b %Y")
                        ts = ts.strftime("%Y-%m-%d")
                    except:
                        ts = "N/A"
                    headlines.append({"title": title, "date": ts, "source": source, "url": link})
    except:
        pass

    # Deduplicate by title
    seen = set()
    unique = []
    for h in headlines:
        if h["title"] not in seen:
            seen.add(h["title"])
            unique.append(h)

    # Simple keyword sentiment
    def sentiment(title):
        pos = ["surge", "gain", "profit", "growth", "record", "order", "buy", "target", "strong", "beat", "win", "up", "rise", "rally"]
        neg = ["fall", "drop", "loss", "debt", "sell", "weak", "miss", "cut", "fraud", "probe", "down", "decline", "concern", "risk"]
        t = title.lower()
        pos_score = sum(1 for w in pos if w in t)
        neg_score = sum(1 for w in neg if w in t)
        if pos_score > neg_score:   return "POSITIVE"
        elif neg_score > pos_score: return "NEGATIVE"
        return "NEUTRAL"

    for h in unique:
        h["sentiment"] = sentiment(h["title"])

    pos_count = sum(1 for h in unique if h["sentiment"] == "POSITIVE")
    neg_count = sum(1 for h in unique if h["sentiment"] == "NEGATIVE")
    overall   = "POSITIVE" if pos_count > neg_count else "NEGATIVE" if neg_count > pos_count else "NEUTRAL"

    return {
        "headlines":          unique[:10],
        "total_headlines":    len(unique),
        "positive_count":     pos_count,
        "negative_count":     neg_count,
        "overall_sentiment":  overall,
        "sentiment_summary":  f"{pos_count} positive, {neg_count} negative out of {len(unique)} articles"
    }
