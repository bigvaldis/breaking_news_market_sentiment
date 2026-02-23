"""Extract breaking financial news from multiple sources."""

import feedparser
import requests
from datetime import datetime, timezone, timedelta

import pandas as pd


def _utcnow():
    return datetime.now(timezone.utc)


# Financial, political, and crypto RSS feeds (no API key required)
RSS_FEEDS = [
    # --- Major Financial ---
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ("CNBC Top News", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("CNBC Business", "https://www.cnbc.com/id/10001147/device/rss/rss.html"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("MarketWatch Pulse", "https://feeds.content.dowjones.io/public/rss/mw_marketpulse"),
    ("Yahoo Finance", "https://finance.yahoo.com/rss/topstories"),
    ("Yahoo Finance Markets", "https://finance.yahoo.com/rss/headline?s=^GSPC"),
    ("Investing.com", "https://www.investing.com/rss/news.rss"),
    ("Investing.com Markets", "https://www.investing.com/rss/news_301.rss"),
    ("Seeking Alpha", "https://seekingalpha.com/market_currents.xml"),
    ("Financial Times", "https://www.ft.com/?format=rss"),
    # --- Macro / Contrarian ---
    ("Zero Hedge", "https://feeds.feedburner.com/zerohedge/feed"),
    # --- Crypto ---
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
    # --- Political / Policy ---
    ("CNN Top Stories", "http://rss.cnn.com/rss/cnn_topstories.rss"),
    ("CNN Politics", "http://rss.cnn.com/rss/cnn_allpolitics.rss"),
    ("CNN Business", "http://rss.cnn.com/rss/money_news_international.rss"),
    ("Fox Business", "https://moxie.foxbusiness.com/google-publisher/latest.xml"),
    ("Fox News Politics", "https://moxie.foxnews.com/google-publisher/politics.xml"),
    ("The Hill", "https://thehill.com/feed/"),
    ("NPR News", "https://feeds.npr.org/1001/rss.xml"),
    ("NPR Business", "https://feeds.npr.org/1006/rss.xml"),
    ("BBC News", "http://feeds.bbci.co.uk/news/rss.xml"),
    ("BBC Business", "http://feeds.bbci.co.uk/news/business/rss.xml"),
    ("ABC News", "https://abcnews.go.com/abcnews/topstories"),
    ("ABC Politics", "https://abcnews.go.com/abcnews/politicsheadlines"),
    # --- Aggregators (Google News) ---
    ("Reuters (Google)", "https://news.google.com/rss/search?q=site:reuters.com+finance&hl=en-US&gl=US&ceid=US:en"),
    ("Google News Business", "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en"),
    ("Google News Economy", "https://news.google.com/rss/search?q=economy+OR+stock+market+OR+federal+reserve&hl=en-US&gl=US&ceid=US:en"),
]

# Trump Truth Social RSS feeds (primary + fallbacks)
TRUMP_RSS_FEEDS = [
    ("Trump (Truth Social)", "https://trumpstruth.org/feed"),
    ("Trump (Truth Social)", "https://trumptruthsocial.com/feed"),
    ("Trump (Truth Social)", "https://rss.app/feeds/v1.1/tsLBMEFKpRdTuPFi.json"),
]

RSS_TIMEOUT = 15


def _fetch_rss_raw(url: str) -> feedparser.FeedParserDict:
    """Fetch RSS with a proper HTTP timeout."""
    try:
        resp = requests.get(url, timeout=RSS_TIMEOUT, headers={"User-Agent": "NewsMarketSentiment/1.0"})
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except Exception:
        return feedparser.parse(url)


def _parse_published(entry) -> datetime | None:
    """Extract published datetime from feed entry, always UTC-aware.

    Returns None if no date can be parsed (caller decides what to do).
    """
    # Try struct_time fields first
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                dt = datetime(*parsed[:6], tzinfo=timezone.utc)
                if dt.year >= 2020:
                    return dt
            except (TypeError, ValueError):
                continue

    # Try raw string fields with dateutil
    for attr in ("published", "updated", "date"):
        raw = getattr(entry, attr, None) or entry.get(attr)
        if raw and isinstance(raw, str):
            try:
                from dateutil import parser as dateutil_parser
                dt = dateutil_parser.parse(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                if dt.year >= 2020:
                    return dt
            except Exception:
                continue

    return None


def fetch_rss_feed(source_name: str, url: str) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    articles = []
    try:
        feed = _fetch_rss_raw(url)
        for entry in feed.entries[:25]:
            published = _parse_published(entry)
            if published is None:
                continue  # skip articles without a parseable date

            articles.append({
                "source": source_name,
                "title": entry.get("title", ""),
                "summary": entry.get("summary", entry.get("description", ""))[:500],
                "url": entry.get("link", ""),
                "published_at": published,
                "fetched_at": _utcnow(),
            })
    except Exception as e:
        print(f"Warning: Failed to fetch {source_name}: {e}")
    return articles


def _clean_html(text: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    import re
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_trump_truth_social() -> list[dict]:
    """Fetch Trump Truth Social posts from multiple RSS sources for reliability."""
    articles = []
    for source_name, url in TRUMP_RSS_FEEDS:
        try:
            feed = _fetch_rss_raw(url)
            if not feed.entries:
                print(f"[Trump RSS] No entries from {url}")
                continue

            for entry in feed.entries[:25]:
                raw_title = entry.get("title", "") or ""
                raw_summary = entry.get("summary", entry.get("description", "")) or ""
                clean_summary = _clean_html(raw_summary)

                # Use title if available; fall back to first 200 chars of summary
                title = raw_title.strip()
                if not title or len(title) < 10 or title.startswith("[No Title]"):
                    title = clean_summary[:200]
                if not title or len(title.strip()) < 10:
                    continue

                published = _parse_published(entry)
                if published is None:
                    published = _utcnow()  # Trump posts are always current

                articles.append({
                    "source": "Trump (Truth Social)",
                    "title": title[:300],
                    "summary": clean_summary[:500],
                    "url": entry.get("link", ""),
                    "published_at": published,
                    "fetched_at": _utcnow(),
                })

            if articles:
                print(f"[Trump RSS] Got {len(articles)} posts from {url}")
                break
        except Exception as e:
            print(f"[Trump RSS] Failed {url}: {e}")
            continue

    if not articles:
        print("[Trump RSS] WARNING: All sources failed — no Trump posts fetched")
    return articles


def fetch_all_news() -> pd.DataFrame:
    """Fetch news from all configured RSS feeds + Trump Truth Social."""
    all_articles = []
    for source_name, url in RSS_FEEDS:
        articles = fetch_rss_feed(source_name, url)
        all_articles.extend(articles)

    # Always fetch Trump Truth Social
    trump_posts = fetch_trump_truth_social()
    all_articles.extend(trump_posts)

    # Optional: Add Trump X tweets if TWITTER_BEARER_TOKEN is set (X API is paid)
    try:
        from src.trump_tweets import fetch_trump_x_tweets
        tweets_df = fetch_trump_x_tweets()
        if not tweets_df.empty:
            tweet_articles = tweets_df.to_dict(orient="records")
            all_articles.extend(tweet_articles)
    except Exception:
        pass

    if not all_articles:
        return pd.DataFrame()

    df = pd.DataFrame(all_articles)

    # Normalize titles for robust dedup (case, whitespace, punctuation)
    import re
    df["_norm"] = df["title"].apply(lambda t: re.sub(r"[^a-z0-9 ]", "", str(t).lower()).strip() if isinstance(t, str) else "")
    df = df.drop_duplicates(subset=["_norm", "source"], keep="first")
    df = df[df["_norm"].str.len() > 10]  # drop empty/garbage titles
    df = df.drop(columns=["_norm"])

    # Drop articles with no parseable date or older than 48 hours
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    df = df.dropna(subset=["published_at"])
    cutoff = _utcnow() - timedelta(hours=48)
    df = df[df["published_at"] >= cutoff]

    df = df.sort_values("published_at", ascending=False).reset_index(drop=True)
    print(f"[News] Fetched {len(df)} fresh articles ({len(trump_posts)} Trump posts)")
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
        published = datetime.fromisoformat(pub.replace("Z", "+00:00")) if pub else _utcnow()
        articles.append({
            "source": a.get("source", {}).get("name", "NewsAPI"),
            "title": a.get("title", ""),
            "summary": (a.get("description") or "")[:500],
            "url": a.get("url", ""),
            "published_at": published,
            "fetched_at": _utcnow(),
        })
    return pd.DataFrame(articles)
