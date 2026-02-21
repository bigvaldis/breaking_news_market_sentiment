"""S&P 500 market data and correlation with news sentiment."""

import threading
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False


SP500_TICKER = "^GSPC"
GOLD_TICKER = "GC=F"  # Gold Futures - tracks spot gold price per oz (~$2500+)
VIX_TICKER = "^VIX"   # CBOE Volatility Index - fear gauge
BTC_TICKER = "BTC-USD"  # Bitcoin spot price

# Serialize yfinance downloads to avoid concurrent requests returning wrong/cached data
_yf_lock = threading.Lock()


def _fetch_ohlc(ticker: str, days: int) -> pd.DataFrame:
    """Fetch OHLC data for a ticker. Shared logic for SP500 and Gold."""
    if not YF_AVAILABLE:
        return pd.DataFrame()

    end = datetime.now()
    start = end - timedelta(days=days)
    try:
        with _yf_lock:
            df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True, threads=False)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            date_col = next((c for c in df.columns if c[0] == "Date"), df.columns[0])
            o = next((c for c in df.columns if c[0] == "Open"), None)
            h = next((c for c in df.columns if c[0] == "High"), None)
            l = next((c for c in df.columns if c[0] == "Low"), None)
            c = next((c for c in df.columns if c[0] == "Close"), None)
            if all(x for x in [o, h, l, c]):
                df = df[[date_col, o, h, l, c]].copy()
                df.columns = ["date", "open", "high", "low", "close"]
        else:
            df.columns = [str(c).lower() for c in df.columns]
        df["date"] = pd.to_datetime(df["date"]).dt.date
        for col in ["open", "high", "low", "close"]:
            if col not in df.columns and col.capitalize() in df.columns:
                df[col] = df[col.capitalize()]
        return df
    except Exception:
        return pd.DataFrame()


def fetch_sp500_history(days: int = 90) -> pd.DataFrame:
    """Fetch S&P 500 daily OHLC data."""
    return _fetch_ohlc(SP500_TICKER, days)


def fetch_gold_history(days: int = 90) -> pd.DataFrame:
    """Fetch Gold (GC=F futures) daily OHLC data."""
    return _fetch_ohlc(GOLD_TICKER, days)


def fetch_vix_history(days: int = 90) -> pd.DataFrame:
    """Fetch VIX (CBOE Volatility Index) daily OHLC data."""
    return _fetch_ohlc(VIX_TICKER, days)


def fetch_btc_history(days: int = 90) -> pd.DataFrame:
    """Fetch Bitcoin (BTC-USD) daily OHLC data."""
    return _fetch_ohlc(BTC_TICKER, days)


def _ohlc_to_list(df: pd.DataFrame) -> list[dict]:
    """Convert OHLC DataFrame to API-ready list."""
    if df.empty or "close" not in df.columns:
        return []
    close_col = "close"
    open_col = "open" if "open" in df.columns else None
    high_col = "high" if "high" in df.columns else None
    low_col = "low" if "low" in df.columns else None
    result = []
    for _, row in df.iterrows():
        r = {"date": str(row["date"]), "close": float(row[close_col])}
        if open_col:
            r["open"] = float(row[open_col])
        if high_col:
            r["high"] = float(row[high_col])
        if low_col:
            r["low"] = float(row[low_col])
        result.append(r)
    return result


def sentiment_history_to_daily(history: list[dict]) -> pd.DataFrame:
    """Aggregate sentiment history to daily averages."""
    if not history:
        return pd.DataFrame()

    rows = []
    for h in history:
        ts = h.get("timestamp")
        score = h.get("overall_score")
        if ts is None or score is None:
            continue
        try:
            dt = pd.to_datetime(ts).date()
            rows.append({"date": dt, "sentiment": float(score)})
        except (TypeError, ValueError):
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    return df.groupby("date", as_index=False)["sentiment"].mean()


def compute_correlation(
    sentiment_history: list[dict],
    sp500_days: int = 60,
) -> dict:
    """
    Correlate news sentiment with S&P 500 returns.
    Returns same-day and 1-day lag correlations.
    """
    if not YF_AVAILABLE:
        return {
            "same_day_correlation": None,
            "lag1_correlation": None,
            "sp500_data": [],
            "aligned_data": [],
            "error": "yfinance_not_installed",
        }

    sp500 = fetch_sp500_history(days=sp500_days)
    sp500_list = []
    if not sp500.empty and ("close" in sp500.columns or "Close" in sp500.columns):
        close_col = "close" if "close" in sp500.columns else "Close"
        open_col = "open" if "open" in sp500.columns else "Open"
        high_col = "high" if "high" in sp500.columns else "High"
        low_col = "low" if "low" in sp500.columns else "Low"
        for _, row in sp500.iterrows():
            r = {"date": str(row["date"]), "close": float(row[close_col])}
            if open_col in sp500.columns:
                r["open"] = float(row[open_col])
            if high_col in sp500.columns:
                r["high"] = float(row[high_col])
            if low_col in sp500.columns:
                r["low"] = float(row[low_col])
            sp500_list.append(r)

    if not sentiment_history:
        return {
            "same_day_correlation": None,
            "lag1_correlation": None,
            "sp500_data": sp500_list,
            "aligned_data": [],
            "error": "no_sentiment_data",
        }

    sent_daily = sentiment_history_to_daily(sentiment_history)

    if sp500.empty or ("close" not in sp500.columns and "Close" not in sp500.columns):
        return {
            "same_day_correlation": None,
            "lag1_correlation": None,
            "sp500_data": sp500_list,
            "aligned_data": [],
            "error": "no_market_data",
        }

    close_col = "close" if "close" in sp500.columns else "Close"
    sp500["date"] = pd.to_datetime(sp500["date"]).dt.date
    sp500["return"] = sp500[close_col].pct_change()

    # Merge on date
    merged = pd.merge(sent_daily, sp500[["date", close_col, "return"]], on="date", how="inner")
    merged = merged.dropna(subset=["return", "sentiment"])

    if len(merged) < 5:
        open_col = "open" if "open" in sp500.columns else "Open"
        high_col = "high" if "high" in sp500.columns else "High"
        low_col = "low" if "low" in sp500.columns else "Low"
        sp500_list = []
        for _, row in sp500.iterrows():
            r = {"date": str(row["date"]), "close": float(row[close_col])}
            if open_col in sp500.columns:
                r["open"] = float(row[open_col])
            if high_col in sp500.columns:
                r["high"] = float(row[high_col])
            if low_col in sp500.columns:
                r["low"] = float(row[low_col])
            sp500_list.append(r)
        return {
            "same_day_correlation": None,
            "lag1_correlation": None,
            "sp500_data": sp500_list,
            "aligned_data": [],
            "error": "insufficient_overlap",
        }

    same_day = round(float(merged["sentiment"].corr(merged["return"])), 4)

    # Lag: sentiment(t) vs return(t+1)
    merged["return_next"] = merged["return"].shift(-1)
    lag_merged = merged.dropna(subset=["sentiment", "return_next"])
    lag1 = round(float(lag_merged["sentiment"].corr(lag_merged["return_next"])), 4) if len(lag_merged) >= 5 else None

    # Serialize for API (date as string, OHLC for candlestick)
    open_col = "open" if "open" in sp500.columns else "Open"
    high_col = "high" if "high" in sp500.columns else "High"
    low_col = "low" if "low" in sp500.columns else "Low"
    sp500_list = []
    for _, row in sp500.iterrows():
        r = {"date": str(row["date"]), "close": float(row[close_col])}
        if open_col in sp500.columns:
            r["open"] = float(row[open_col])
        if high_col in sp500.columns:
            r["high"] = float(row[high_col])
        if low_col in sp500.columns:
            r["low"] = float(row[low_col])
        sp500_list.append(r)

    aligned_list = [
        {"date": str(row["date"]), "sentiment": row["sentiment"], "return": row["return"], "close": row[close_col]}
        for _, row in merged.iterrows()
    ]

    return {
        "same_day_correlation": same_day,
        "lag1_correlation": lag1,
        "sp500_data": sp500_list,
        "aligned_data": aligned_list,
        "samples": len(merged),
    }
