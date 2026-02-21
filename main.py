#!/usr/bin/env python3
"""
News & Market Sentiment Analysis

Extracts breaking financial news and tracks market sentiment over time.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from src.news_extractor import fetch_all_news, fetch_news_api
from src.sentiment_analyzer import (
    analyze_sentiment_vader,
    get_market_sentiment_summary,
)
from src.sentiment_tracker import (
    append_sentiment_summary,
    get_sentiment_trend,
    load_sentiment_history,
    save_news,
)

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent / "data"


def run_pipeline(use_news_api: bool = False) -> dict:
    """
    Run full pipeline: fetch news -> analyze sentiment -> save & track.
    Returns current sentiment summary and trend.
    """
    # 1. Fetch news
    if use_news_api and os.getenv("NEWSAPI_KEY"):
        df = fetch_news_api(os.getenv("NEWSAPI_KEY"))
        if df.empty:
            df = fetch_all_news()
    else:
        df = fetch_all_news()

    if df.empty:
        print("No news fetched. Check your internet connection or RSS feeds.")
        return {"error": "no_news"}

    print(f"Fetched {len(df)} articles")

    # 2. Analyze sentiment
    df = analyze_sentiment_vader(df)
    summary = get_market_sentiment_summary(df)

    # 3. Save and track
    save_news(df, DATA_DIR)
    append_sentiment_summary(summary, DATA_DIR)

    # 4. Trend
    history = load_sentiment_history(DATA_DIR)
    trend = get_sentiment_trend(history)

    result = {**summary, "trend": trend["trend"], "recent_avg": trend["recent_avg"]}
    return result


def print_report(result: dict) -> None:
    """Print a human-readable sentiment report."""
    if "error" in result:
        return
    print("\n" + "=" * 50)
    print("FINANCIAL MARKET SENTIMENT REPORT")
    print("=" * 50)
    print(f"Overall sentiment: {result.get('sentiment_label', 'N/A').upper()}")
    print(f"Score: {result.get('overall_score', 0):.3f} (-1 to +1)")
    print(f"Articles analyzed: {result.get('article_count', 0)}")
    print(f"Positive: {result.get('positive_pct', 0):.1f}% | "
          f"Negative: {result.get('negative_pct', 0):.1f}% | "
          f"Neutral: {result.get('neutral_pct', 0):.1f}%")
    print(f"Trend: {result.get('trend', 'N/A')}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    result = run_pipeline(use_news_api=True)
    print_report(result)
