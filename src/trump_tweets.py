"""Optional: Fetch Trump posts for sentiment analysis.

Truth Social: Free RSS feed at trumpstruth.org/feed — already included in RSS_FEEDS.
X (Twitter): Requires paid X API v2. Set TWITTER_BEARER_TOKEN in .env to add X tweets.
"""

import os
from datetime import datetime

import pandas as pd
import requests


TRUMP_USER_ID = "25073877"  # @realDonaldTrump on X


def fetch_trump_x_tweets() -> pd.DataFrame:
    """
    Fetch recent tweets from Trump's X account via X API v2.
    Returns empty DataFrame if TWITTER_BEARER_TOKEN is not set.
    X API is paid — use Truth Social RSS (in RSS_FEEDS) for free Trump content.
    """
    token = os.getenv("TWITTER_BEARER_TOKEN")
    if not token:
        return pd.DataFrame()

    url = "https://api.twitter.com/2/users/{}/tweets".format(TRUMP_USER_ID)
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "max_results": 20,
        "tweet.fields": "created_at,text",
        "exclude": "retweets,replies",
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Trump X tweets fetch error: {e}")
        return pd.DataFrame()

    articles = []
    for t in data.get("data", []):
        text = t.get("text", "")
        if not text or len(text) < 10:
            continue
        pub = t.get("created_at")
        published = datetime.fromisoformat(pub.replace("Z", "+00:00")) if pub else datetime.now()
        articles.append({
            "source": "Trump (X)",
            "title": text[:200],
            "summary": text[:500],
            "url": "",
            "published_at": published,
            "fetched_at": datetime.now(),
        })
    return pd.DataFrame(articles)
