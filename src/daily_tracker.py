"""Daily snapshot tracker for data science: sentiment vs market indicators.

Each pipeline run appends a row to data/daily_tracker.csv with:
- Date & timestamp
- Average sentiment score & label (overall + per source category)
- Crypto Fear & Greed Index
- Wall Street (CNN) Fear & Greed Index
- S&P 500 close, Gold close, VIX close, BTC close

Also saves per-source sentiment breakdown to data/source_sentiment.csv
for correlation analysis between news types and market movement.
"""

import math
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd

TRACKER_CSV = "daily_tracker.csv"
SOURCE_SENTIMENT_CSV = "source_sentiment.csv"

COLUMNS = [
    "date",
    "timestamp",
    "sentiment_score",
    "sentiment_label",
    "positive_pct",
    "neutral_pct",
    "negative_pct",
    "article_count",
    "crypto_fear_greed_value",
    "crypto_fear_greed_label",
    "wall_street_fear_greed_value",
    "wall_street_fear_greed_label",
    "sp500_close",
    "gold_close",
    "vix_close",
    "btc_close",
]

# Map raw source names to clean categories for correlation analysis
SOURCE_CATEGORIES = {
    "Bloomberg Markets": "Bloomberg",
    "CNBC Top News": "CNBC",
    "CNBC Business": "CNBC",
    "Dow Jones": "Dow Jones / MarketWatch",
    "Yahoo Finance": "Yahoo Finance",
    "Reuters Business": "Reuters",
    "CNN Top Stories": "CNN",
    "CNN Politics": "CNN",
    "CNN Business": "CNN",
    "BBC News": "BBC",
    "BBC Business": "BBC",
    "ABC News": "ABC News",
    "ABC Politics": "ABC News",
    "Trump (Truth Social)": "Trump Truth Social",
    "Trump (X)": "Trump Truth Social",
}


def _safe_float(val):
    """Convert to float or None."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except (TypeError, ValueError):
        return None


def _latest_close(fetch_fn, days=7):
    """Get the most recent closing price from an OHLC fetch function."""
    try:
        df = fetch_fn(days=days)
        if df.empty or "close" not in df.columns:
            return None
        return _safe_float(df["close"].iloc[-1])
    except Exception:
        return None


def _categorize_source(source: str) -> str:
    """Map raw source name to a clean category."""
    if not source:
        return "Other"
    for key, cat in SOURCE_CATEGORIES.items():
        if key.lower() in str(source).lower():
            return cat
    return "Other"


def collect_daily_snapshot(
    sentiment_summary: dict,
    data_dir: Path,
    news_df: pd.DataFrame = None,
) -> dict:
    """Collect all indicators and append to daily_tracker.csv.

    If news_df is provided (with sentiment_compound column), also saves
    per-source sentiment breakdown to source_sentiment.csv.

    Returns the snapshot dict for logging/debugging.
    """
    from src.fear_greed import fetch_fear_greed
    from src.wall_street_fear_greed import fetch_wall_street_fear_greed
    from src.market_data import (
        fetch_sp500_history,
        fetch_gold_history,
        fetch_vix_history,
        fetch_btc_history,
    )

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    # Sentiment
    score = _safe_float(sentiment_summary.get("overall_score"))
    label = sentiment_summary.get("sentiment_label", "unknown")

    # Crypto Fear & Greed
    cfg = fetch_fear_greed()
    crypto_fg_val = cfg.get("value") if not cfg.get("error") else None
    crypto_fg_label = cfg.get("classification") if not cfg.get("error") else None

    # Wall Street (CNN) Fear & Greed
    wsfg = fetch_wall_street_fear_greed()
    ws_fg_val = wsfg.get("value") if not wsfg.get("error") else None
    ws_fg_label = wsfg.get("classification") if not wsfg.get("error") else None

    # Market closes
    sp500 = _latest_close(fetch_sp500_history)
    gold = _latest_close(fetch_gold_history)
    vix = _latest_close(fetch_vix_history)
    btc = _latest_close(fetch_btc_history)

    snapshot = {
        "date": date_str,
        "timestamp": now.isoformat(),
        "sentiment_score": score,
        "sentiment_label": label,
        "positive_pct": _safe_float(sentiment_summary.get("positive_pct")),
        "neutral_pct": _safe_float(sentiment_summary.get("neutral_pct")),
        "negative_pct": _safe_float(sentiment_summary.get("negative_pct")),
        "article_count": sentiment_summary.get("article_count"),
        "crypto_fear_greed_value": crypto_fg_val,
        "crypto_fear_greed_label": crypto_fg_label,
        "wall_street_fear_greed_value": ws_fg_val,
        "wall_street_fear_greed_label": ws_fg_label,
        "sp500_close": sp500,
        "gold_close": gold,
        "vix_close": vix,
        "btc_close": btc,
    }

    _append_snapshot(snapshot, data_dir)

    # Per-source sentiment breakdown
    if news_df is not None and not news_df.empty and "sentiment_compound" in news_df.columns:
        market_data = {
            "sp500_close": sp500,
            "gold_close": gold,
            "vix_close": vix,
            "btc_close": btc,
            "crypto_fear_greed_value": crypto_fg_val,
            "wall_street_fear_greed_value": ws_fg_val,
        }
        _save_source_sentiment(news_df, date_str, now, market_data, data_dir)

    return snapshot


def _save_source_sentiment(
    df: pd.DataFrame, date_str: str, now: datetime,
    market_data: dict, data_dir: Path,
) -> None:
    """Save per-source-category average sentiment with market data."""
    df = df.copy()
    df["_category"] = df["source"].apply(_categorize_source)

    grouped = df.groupby("_category").agg(
        avg_sentiment=("sentiment_compound", "mean"),
        article_count=("sentiment_compound", "count"),
    ).reset_index()

    rows = []
    for _, g in grouped.iterrows():
        rows.append({
            "date": date_str,
            "timestamp": now.isoformat(),
            "source_category": g["_category"],
            "avg_sentiment": _safe_float(g["avg_sentiment"]),
            "article_count": int(g["article_count"]),
            **{k: v for k, v in market_data.items()},
        })

    if not rows:
        return

    data_dir.mkdir(parents=True, exist_ok=True)
    filepath = data_dir / SOURCE_SENTIMENT_CSV
    row_df = pd.DataFrame(rows)

    if filepath.exists():
        row_df.to_csv(filepath, mode="a", header=False, index=False)
    else:
        row_df.to_csv(filepath, index=False)


def _append_snapshot(snapshot: dict, data_dir: Path) -> None:
    """Append snapshot row to CSV, creating file if needed."""
    data_dir.mkdir(parents=True, exist_ok=True)
    filepath = data_dir / TRACKER_CSV

    row_df = pd.DataFrame([snapshot], columns=COLUMNS)

    if filepath.exists():
        row_df.to_csv(filepath, mode="a", header=False, index=False)
    else:
        row_df.to_csv(filepath, index=False)


def load_daily_tracker(data_dir: Path) -> pd.DataFrame:
    """Load the daily tracker CSV for analysis."""
    filepath = data_dir / TRACKER_CSV
    if not filepath.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(filepath)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def load_source_sentiment(data_dir: Path) -> pd.DataFrame:
    """Load the per-source sentiment CSV."""
    filepath = data_dir / SOURCE_SENTIMENT_CSV
    if not filepath.exists():
        return pd.DataFrame()
    df = pd.read_csv(filepath)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


INDICATORS = ["sp500_close", "gold_close", "vix_close", "btc_close",
              "crypto_fear_greed_value", "wall_street_fear_greed_value"]
INDICATOR_LABELS = {
    "sp500_close": "S&P 500",
    "gold_close": "Gold",
    "vix_close": "VIX",
    "btc_close": "BTC",
    "crypto_fear_greed_value": "Crypto F&G",
    "wall_street_fear_greed_value": "WS F&G",
}

TIME_PERIODS = [
    {"key": "1d", "label": "1 Day", "days": 1},
    {"key": "3d", "label": "3 Days", "days": 3},
    {"key": "7d", "label": "7 Days", "days": 7},
    {"key": "15d", "label": "15 Days", "days": 15},
    {"key": "1m", "label": "1 Month", "days": 30},
    {"key": "1q", "label": "1 Quarter", "days": 90},
    {"key": "6m", "label": "6 Months", "days": 180},
    {"key": "1y", "label": "1 Year", "days": 365},
]


def _compute_corr_for_period(source_df, tracker_df, cutoff_date):
    """Compute one correlation matrix for data on or after cutoff_date."""
    sdf = source_df[source_df["date"] >= cutoff_date] if not source_df.empty else source_df
    tdf = tracker_df[tracker_df["date"] >= cutoff_date] if not tracker_df.empty else tracker_df

    if sdf.empty and tdf.empty:
        return {}, [], 0

    # Aggregate to daily averages per source category
    if not sdf.empty:
        daily = sdf.groupby(["date", "source_category"]).agg(
            avg_sentiment=("avg_sentiment", "mean"),
            **{ind: (ind, "first") for ind in INDICATORS if ind in sdf.columns},
        ).reset_index()
        categories = sorted(daily["source_category"].unique().tolist())
    else:
        daily = pd.DataFrame()
        categories = []

    n_days = daily["date"].nunique() if not daily.empty else 0

    matrix = {}
    for cat in categories:
        cat_data = daily[daily["source_category"] == cat].copy()
        row = {}
        for ind in INDICATORS:
            if ind not in cat_data.columns:
                row[INDICATOR_LABELS[ind]] = None
                continue
            valid = cat_data[["avg_sentiment", ind]].dropna()
            if len(valid) < 3:
                row[INDICATOR_LABELS[ind]] = None
            else:
                corr = valid["avg_sentiment"].corr(valid[ind])
                row[INDICATOR_LABELS[ind]] = _safe_float(corr)
        matrix[cat] = row

    # Overall sentiment
    if not tdf.empty:
        overall_row = {}
        for ind in INDICATORS:
            if ind not in tdf.columns:
                overall_row[INDICATOR_LABELS[ind]] = None
                continue
            valid = tdf[["sentiment_score", ind]].dropna()
            if len(valid) < 3:
                overall_row[INDICATOR_LABELS[ind]] = None
            else:
                corr = valid["sentiment_score"].corr(valid[ind])
                overall_row[INDICATOR_LABELS[ind]] = _safe_float(corr)
        matrix["Overall Sentiment"] = overall_row

    return matrix, categories, n_days


def compute_correlation_matrix(data_dir: Path, period_key: str = None) -> dict:
    """Compute correlation matrices for all time periods.

    If period_key is given, returns only that period.
    Otherwise returns all periods.

    Returns dict with:
      - periods: list of {key, label, days_in_period, days_available, matrix, categories}
      - indicators: list of indicator names
      - data_start: earliest date in the dataset
      - total_days: total unique dates collected
      - message: status message
    """
    source_df = load_source_sentiment(data_dir)
    tracker_df = load_daily_tracker(data_dir)

    all_dates = set()
    if not source_df.empty and "date" in source_df.columns:
        all_dates.update(source_df["date"].dropna().unique())
    if not tracker_df.empty and "date" in tracker_df.columns:
        all_dates.update(tracker_df["date"].dropna().unique())

    if not all_dates:
        return {
            "periods": [],
            "indicators": [INDICATOR_LABELS[i] for i in INDICATORS],
            "data_start": None,
            "total_days": 0,
            "message": "No data yet. Run the pipeline daily to accumulate correlation data.",
        }

    from datetime import date, timedelta
    today = date.today()
    data_start = min(all_dates)
    total_days = len(all_dates)

    periods_to_compute = TIME_PERIODS
    if period_key:
        periods_to_compute = [p for p in TIME_PERIODS if p["key"] == period_key] or TIME_PERIODS

    result_periods = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for p in periods_to_compute:
            cutoff = today - timedelta(days=p["days"])
            matrix, categories, days_avail = _compute_corr_for_period(source_df, tracker_df, cutoff)
            all_cats = (["Overall Sentiment"] + categories) if "Overall Sentiment" in matrix else categories
            result_periods.append({
                "key": p["key"],
                "label": p["label"],
                "days_in_period": p["days"],
                "days_available": days_avail,
                "matrix": matrix,
                "categories": all_cats,
            })

    return {
        "periods": result_periods,
        "indicators": [INDICATOR_LABELS[i] for i in INDICATORS],
        "data_start": str(data_start),
        "total_days": total_days,
        "message": f"Collecting since {data_start} ({total_days} day(s)). Need 5+ days for meaningful correlations.",
    }
