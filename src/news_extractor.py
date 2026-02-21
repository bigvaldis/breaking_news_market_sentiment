"""Extract breaking financial news from multiple sources."""

import feedparser
import requests
from datetime import datetime

import pandas as pd


# Financial news RSS feeds (no API key required)
RSS_FEEDS = [
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ("CNBC Top News", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("Dow Jones", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("Yahoo Finance", "https://feeds.finance.yahoo.com/rss/2.0/headline"),
    ("Reuters Business", "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best"),
]


def fetch_rss_feed(source_name: str, url: str) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:  # Limit per source
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6])
                except (TypeError, ValueError):
                    published = datetime.now()
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                try:
                    published = datetime(*entry.updated_parsed[:6])
                except (TypeError, ValueError):
                    published = datetime.now()
            else:
                published = datetime.now()

            articles.append({
                "source": source_name,
                "title": entry.get("title", ""),
                "summary": entry.get("summary", entry.get("description", ""))[:500],
                "url": entry.get("link", ""),
                "published_at": published,
                "fetched_at": datetime.now(),
            })
    except Exception as e:
        print(f"Warning: Failed to fetch {source_name}: {e}")
    return articles


def fetch_all_news() -> pd.DataFrame:
    """Fetch news from all configured RSS feeds."""
    all_articles = []
    for source_name, url in RSS_FEEDS:
        articles = fetch_rss_feed(source_name, url)
        all_articles.extend(articles)

    if not all_articles:
        return pd.DataFrame()

    df = pd.DataFrame(all_articles)
    df = df.drop_duplicates(subset=["title", "source"], keep="first")
    df = df.sort_values("published_at", ascending=False).reset_index(drop=True)
    return df


def fetch_news_api(api_key: str, query: str = "stock market OR economy OR Federal Reserve") -> pd.DataFrame:
    """Fetch news from NewsAPI.org (requires API key)."""
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "apiKey": api_key,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 50,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"NewsAPI error: {e}")
        return pd.DataFrame()

    articles = []
    for a in data.get("articles", []):
        if not a.get("title") or a.get("title") == "[Removed]":
            continue
        pub = a.get("publishedAt")
        published = datetime.fromisoformat(pub.replace("Z", "+00:00")) if pub else datetime.now()
        articles.append({
            "source": a.get("source", {}).get("name", "NewsAPI"),
            "title": a.get("title", ""),
            "summary": (a.get("description") or "")[:500],
            "url": a.get("url", ""),
            "published_at": published,
            "fetched_at": datetime.now(),
        })
    return pd.DataFrame(articles)
