"""Store and track financial sentiment over time.

Two-file design:
  news_latest.csv  — overwritten each pipeline run (source for /api/news)
  news_archive.csv — append-only historical log (source for ML/correlation)
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data"
NEWS_LATEST_CSV = "news_latest.csv"
NEWS_ARCHIVE_CSV = "news_archive.csv"
SENTIMENT_HISTORY_JSON = "sentiment_history.json"


def ensure_data_dir(path: Path = DEFAULT_DB_PATH) -> Path:
    """Create data directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_title(t):
    """Normalize title for dedup: lowercase, strip whitespace/punctuation."""
    if not isinstance(t, str):
        return ""
    return re.sub(r"[^a-z0-9 ]", "", t.lower()).strip()


def save_news(df: pd.DataFrame, path: Path = DEFAULT_DB_PATH) -> None:
    """Save pipeline results to both live feed and archive.

    news_latest.csv — fully replaced each run (what users see).
    news_archive.csv — append-only, deduped, for long-term ML data.
    """
    ensure_data_dir(path)

    # 1. Live feed: overwrite with this run's fresh articles
    latest_path = path / NEWS_LATEST_CSV
    df.to_csv(latest_path, index=False)

    # 2. Archive: append new articles, keep originals for history
    archive_path = path / NEWS_ARCHIVE_CSV
    if archive_path.exists():
        existing = pd.read_csv(archive_path)
        existing["published_at"] = pd.to_datetime(existing["published_at"], format="mixed", utc=True, errors="coerce")
        existing["fetched_at"] = pd.to_datetime(existing["fetched_at"], format="mixed", utc=True, errors="coerce")

        combined = pd.concat([df, existing], ignore_index=True)
        combined["_norm"] = combined["title"].apply(_normalize_title)
        combined = combined.drop_duplicates(subset=["_norm", "source"], keep="first")
        combined = combined.drop(columns=["_norm"], errors="ignore")
    else:
        combined = df

    combined.to_csv(archive_path, index=False)


def load_news(path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Load latest pipeline results (for the news feed).

    Falls back to the archive if news_latest.csv hasn't been created yet
    (e.g., first deploy after the two-file migration).
    """
    for filename in (NEWS_LATEST_CSV, NEWS_ARCHIVE_CSV):
        fpath = path / filename
        if fpath.exists() and fpath.stat().st_size > 100:
            df = pd.read_csv(fpath)
            for col in ["published_at", "fetched_at"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], format="mixed", utc=True, errors="coerce")
            return df

    return pd.DataFrame()


def load_archive(path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Load full historical archive (for ML, daily snapshots, correlation)."""
    archive_path = path / NEWS_ARCHIVE_CSV
    if not archive_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(archive_path)
    for col in ["published_at", "fetched_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="mixed", utc=True, errors="coerce")
    return df


def append_sentiment_summary(summary: dict, path: Path = DEFAULT_DB_PATH) -> None:
    """Append current sentiment summary to history for trend tracking."""
    ensure_data_dir(path)
    filepath = path / SENTIMENT_HISTORY_JSON
    record = {**summary, "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

    if filepath.exists():
        with open(filepath) as f:
            history = json.load(f)
    else:
        history = []

    history.append(record)
    with open(filepath, "w") as f:
        json.dump(history[-500:], f, indent=2)  # Keep last 500 snapshots


def load_sentiment_history(path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """Load sentiment history for trend analysis."""
    filepath = path / SENTIMENT_HISTORY_JSON
    if not filepath.exists():
        return []
    with open(filepath) as f:
        return json.load(f)


def get_sentiment_trend(history: list[dict], last_n: int = 24) -> dict:
    """
    Compute trend from recent sentiment snapshots.
    last_n: number of most recent records to consider.
    """
    if not history or last_n <= 0:
        return {"trend": "unknown", "recent_avg": 0.0, "samples": 0}

    recent = history[-last_n:]
    scores = [h["overall_score"] for h in recent if "overall_score" in h]
    if not scores:
        return {"trend": "unknown", "recent_avg": 0.0, "samples": 0}

    avg = sum(scores) / len(scores)
    if len(scores) >= 2:
        first_half = sum(scores[: len(scores) // 2]) / (len(scores) // 2)
        second_half = sum(scores[len(scores) // 2 :]) / (len(scores) - len(scores) // 2)
        trend = "improving" if second_half > first_half else "declining" if second_half < first_half else "stable"
    else:
        trend = "stable"

    return {
        "trend": trend,
        "recent_avg": round(avg, 4),
        "samples": len(scores),
    }
