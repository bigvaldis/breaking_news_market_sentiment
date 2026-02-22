"""Flask API for News & Market Sentiment Analysis."""

import math
import os
import threading
from datetime import datetime
from pathlib import Path

import pandas as pd

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from src.news_extractor import fetch_all_news, fetch_news_api
from src.news_filter import filter_and_rank_news, classify_news_type
from src.sentiment_analyzer import (
    analyze_sentiment_vader,
    get_market_sentiment_summary,
)
from src.sentiment_tracker import (
    append_sentiment_summary,
    get_sentiment_trend,
    load_news,
    load_sentiment_history,
    save_news,
)
from src.fear_greed import fetch_fear_greed
from src.wall_street_fear_greed import fetch_wall_street_fear_greed
from src.market_data import fetch_btc_history, fetch_gold_history, fetch_sp500_history, fetch_vix_history, _ohlc_to_list
from src.daily_tracker import collect_daily_snapshot, load_daily_tracker, compute_correlation_matrix

load_dotenv()

# ---------------------------------------------------------------------------
# Server-side cache for market trackers (refreshed every 15 min by scheduler)
# ---------------------------------------------------------------------------
_cache_lock = threading.Lock()
_market_cache = {
    "markets": {"sp500_data": [], "gold_data": [], "vix_data": [], "btc_data": []},
    "fear_greed": {},
    "wall_street_fear_greed": {},
    "last_updated": None,
}


def _refresh_market_cache():
    """Fetch all market trackers + F&G indices and update the in-memory cache."""
    try:
        sp500_df = fetch_sp500_history(days=90)
        gold_df = fetch_gold_history(days=90)
        vix_df = fetch_vix_history(days=90)
        btc_df = fetch_btc_history(days=90)
        fg = fetch_fear_greed()
        ws_fg = fetch_wall_street_fear_greed()
        with _cache_lock:
            _market_cache["markets"] = {
                "sp500_data": _ohlc_to_list(sp500_df),
                "gold_data": _ohlc_to_list(gold_df),
                "vix_data": _ohlc_to_list(vix_df),
                "btc_data": _ohlc_to_list(btc_df),
            }
            _market_cache["fear_greed"] = fg
            _market_cache["wall_street_fear_greed"] = ws_fg
            _market_cache["last_updated"] = datetime.utcnow().isoformat() + "Z"
        print(f"[Market cache] Refreshed at {_market_cache['last_updated']}")
    except Exception as e:
        print(f"[Market cache] Refresh failed: {e}")

# Use DATA_DIR env var if set (e.g. Render disk mount path). Default: project/data
_data_dir = os.getenv("DATA_DIR")
DATA_DIR = Path(_data_dir) if _data_dir else Path(__file__).resolve().parent.parent / "data"
app = Flask(__name__)
CORS(app)


def run_pipeline(use_news_api: bool = False) -> dict:
    """Run news pipeline: fetch, filter, analyze, save. Runs every hour."""
    df = fetch_all_news()

    if use_news_api and os.getenv("NEWSAPI_KEY"):
        try:
            api_df = fetch_news_api(os.getenv("NEWSAPI_KEY"))
            if not api_df.empty:
                df = pd.concat([df, api_df], ignore_index=True)
                df = df.drop_duplicates(subset=["title", "source"], keep="first")
                df = df.sort_values("published_at", ascending=False).reset_index(drop=True)
                print(f"[Pipeline] Combined RSS ({len(df) - len(api_df)}) + NewsAPI ({len(api_df)}) articles")
        except Exception as e:
            print(f"[Pipeline] NewsAPI failed (non-fatal): {e}")

    if df.empty:
        return {"error": "no_news"}

    df = filter_and_rank_news(df)
    if df.empty:
        return {"error": "no_news", "message": "No financial or political news matched filters"}

    df = analyze_sentiment_vader(df)
    summary = get_market_sentiment_summary(df)
    save_news(df, DATA_DIR)
    append_sentiment_summary(summary, DATA_DIR)

    history = load_sentiment_history(DATA_DIR)
    trend = get_sentiment_trend(history)
    return {**summary, "trend": trend["trend"], "recent_avg": trend["recent_avg"]}


def _run_daily_snapshot():
    """Collect daily tracker snapshot after market close.

    Recomputes sentiment from ALL articles published in the full trading day
    window (previous day 21:00 UTC through today 21:30 UTC), which covers
    overnight, premarket (4 AM ET), regular hours, and after-hours.
    """
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    try:
        df = load_news(DATA_DIR)
        if df.empty or "sentiment_compound" not in df.columns:
            print("[Daily snapshot] No analyzed news yet, skipping.")
            return

        now = _dt.now(_tz.utc)
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
        window_start = (now - _td(hours=24, minutes=30)).replace(hour=21, minute=0, second=0)
        trading_day_df = df[(df["published_at"] >= window_start) & (df["published_at"] <= now)]

        if trading_day_df.empty:
            trading_day_df = df[df["published_at"] >= now - _td(hours=24)]

        if trading_day_df.empty or "sentiment_compound" not in trading_day_df.columns:
            print("[Daily snapshot] No articles in trading window, skipping.")
            return

        summary = get_market_sentiment_summary(trading_day_df)
        snapshot = collect_daily_snapshot(summary, DATA_DIR, news_df=trading_day_df)
        print(f"[Daily snapshot] {snapshot.get('date')}: score={snapshot.get('sentiment_score')}, "
              f"articles={summary.get('article_count')} (full trading day)")
    except Exception as e:
        print(f"[Daily snapshot] Failed: {e}")


def _sanitize_value(v):
    """Replace NaN/Inf/NA with None for JSON."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
    except (TypeError, ValueError):
        pass
    return v


def df_to_news_list(df):
    """Convert news DataFrame to JSON-serializable list."""
    if df.empty:
        return []
    df = df.copy()
    for col in ["published_at", "fetched_at"]:
        if col in df.columns:
            s = pd.to_datetime(df[col], utc=True, errors="coerce")
            df[col] = s.apply(lambda x: x.strftime("%Y-%m-%dT%H:%M:%SZ") if pd.notna(x) else None)
    records = df.to_dict(orient="records")
    for r in records:
        for k in list(r.keys()):
            r[k] = _sanitize_value(r[k])
    return records


@app.route("/api/pipeline/run", methods=["POST"])
def run_pipeline_endpoint():
    """Trigger pipeline run and return summary."""
    result = run_pipeline(use_news_api=True)
    return jsonify(result)


def _clean_for_json(obj):
    """Recursively replace NaN/Inf with None for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_for_json(x) for x in obj]
    try:
        if isinstance(obj, (int, str, bool)) or obj is None:
            return obj
        f = float(obj)
        if math.isnan(f) or math.isinf(f):
            return None
    except (TypeError, ValueError):
        pass
    return obj


@app.route("/api/news")
def get_news():
    """Get latest news with pagination. Supports ?page=1&per_page=30&hours=24."""
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    df = load_news(DATA_DIR)
    if df.empty:
        return jsonify({"news": [], "total": 0, "page": 1, "per_page": 30, "has_more": False})

    df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    now = _dt.now(_tz.utc)
    hours = int(request.args.get("hours", 24))

    fresh = df[df["published_at"] >= now - _td(hours=hours)]
    if len(fresh) < 5 and hours <= 24:
        fresh = df[df["published_at"] >= now - _td(hours=48)]

    fresh = fresh.sort_values("published_at", ascending=False)

    total = len(fresh)
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(10, int(request.args.get("per_page", 30))))
    start = (page - 1) * per_page
    page_df = fresh.iloc[start:start + per_page]

    records = df_to_news_list(page_df)
    records = [r for r in records if r.get("title")]
    for r in records:
        if not r.get("news_type"):
            r["news_type"] = classify_news_type(r.get("title", ""), r.get("summary", ""), r.get("source", ""))
    return jsonify({
        "news": _clean_for_json(records),
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_more": start + per_page < total,
    })


@app.route("/api/sentiment-summary")
def get_sentiment_summary():
    """Get latest sentiment summary."""
    history = load_sentiment_history(DATA_DIR)
    if not history:
        return jsonify({"error": "no_data", "message": "Run the pipeline first"})
    latest = history[-1]
    trend = get_sentiment_trend(history)
    return jsonify({**latest, "trend": trend["trend"], "recent_avg": trend["recent_avg"]})


@app.route("/api/sentiment-history")
def get_sentiment_history():
    """Get sentiment history for charts."""
    history = load_sentiment_history(DATA_DIR)
    return jsonify({"history": history})


@app.route("/api/daily-tracker")
def get_daily_tracker():
    """Daily sentiment vs market indicators for data science."""
    df = load_daily_tracker(DATA_DIR)
    if df.empty:
        return jsonify({"data": [], "message": "No snapshots yet. Run the pipeline to start collecting."})
    records = df.to_dict(orient="records")
    return jsonify({"data": _clean_for_json(records), "count": len(records)})


@app.route("/api/correlation-matrix")
def get_correlation_matrix():
    """Correlation matrix: news source sentiment vs market indicators."""
    period = request.args.get("period")
    result = compute_correlation_matrix(DATA_DIR, period_key=period)
    return jsonify(_clean_for_json(result))


@app.route("/api/fear-greed")
def get_fear_greed():
    """Crypto Fear & Greed Index (served from 15-min cache)."""
    with _cache_lock:
        result = _market_cache["fear_greed"].copy()
        result["cache_updated"] = _market_cache["last_updated"]
    return jsonify(result)


@app.route("/api/wall-street-fear-greed")
def get_wall_street_fear_greed():
    """Wall Street (CNN) Fear & Greed Index (served from 15-min cache)."""
    with _cache_lock:
        result = _market_cache["wall_street_fear_greed"].copy()
        result["cache_updated"] = _market_cache["last_updated"]
    return jsonify(result)


@app.route("/api/markets")
def get_markets():
    """S&P 500, Gold, VIX, BTC OHLC (served from 15-min cache)."""
    with _cache_lock:
        data = _market_cache["markets"].copy()
        data["cache_updated"] = _market_cache["last_updated"]
    resp = jsonify(data)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@app.route("/api/markets/sp500")
def get_sp500():
    """S&P 500 only (served from 15-min cache)."""
    with _cache_lock:
        data = _market_cache["markets"].get("sp500_data", [])
    resp = jsonify({"asset": "sp500", "data": data})
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@app.route("/api/markets/gold")
def get_gold():
    """Gold only (served from 15-min cache)."""
    with _cache_lock:
        data = _market_cache["markets"].get("gold_data", [])
    resp = jsonify({"asset": "gold", "data": data})
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@app.route("/api/markets/vix")
def get_vix():
    """VIX only (served from 15-min cache)."""
    with _cache_lock:
        data = _market_cache["markets"].get("vix_data", [])
    resp = jsonify({"asset": "vix", "data": data})
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@app.route("/api/health")
def health():
    """Health check with schedule info."""
    with _cache_lock:
        cache_updated = _market_cache["last_updated"]
    return jsonify({
        "status": "ok",
        "market_cache_updated": cache_updated,
        "schedule": {
            "market_refresh": f"every {os.getenv('MARKET_REFRESH_MINUTES', '15')} min",
            "news_pipeline": f"every {os.getenv('NEWS_PIPELINE_MINUTES', '60')} min",
            "daily_snapshot": f"{os.getenv('DAILY_SNAPSHOT_HOUR', '21')}:{os.getenv('DAILY_SNAPSHOT_MINUTE', '30')} UTC",
        },
    })


# Production: serve built React app when frontend/dist exists
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIST, "index.html")

    @app.route("/<path:path>")
    def serve_static(path):
        if path.startswith("api"):
            from flask import abort
            abort(404)  # API routes are registered above; avoid serving index.html
        file_path = FRONTEND_DIST / path
        if file_path.is_file():
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")
else:
    @app.route("/")
    def index_fallback():
        return (
            "<h1>Frontend not built</h1>"
            "<p>Run <code>cd frontend && npm run build</code> then restart Flask.</p>"
            "<p>Or use <code>./start.sh</code> for dev (React on :3000, API on :5001).</p>"
            "<p><a href='/api/health'>API health</a></p>",
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )


def _locked_run(job_name, fn, *args, **kwargs):
    """Run a function with a file lock (safe for Gunicorn multi-worker)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = DATA_DIR / f".{job_name}.lock"
    try:
        from filelock import FileLock
        lock = FileLock(lock_path, timeout=150)
        with lock:
            return fn(*args, **kwargs)
    except Exception as e:
        print(f"[{job_name}] Failed: {e}")


def _scheduled_market_refresh():
    """Refresh market data + F&G cache (every 15 min)."""
    _refresh_market_cache()


def _scheduled_news_pipeline():
    """Fetch and analyze news (every 1 hour)."""
    result = _locked_run("news_pipeline", run_pipeline, use_news_api=True)
    if result:
        print(f"[News pipeline] {result.get('article_count', 0)} articles, score={result.get('overall_score')}")


def _scheduled_daily_snapshot():
    """Collect daily snapshot for ML/correlation (after market close)."""
    _locked_run("daily_snapshot", _run_daily_snapshot)


def _start_schedulers():
    """Start all three background schedulers.

    1. Market trackers + F&G: every 15 minutes
    2. News pipeline: every 1 hour
    3. Daily tracker snapshot: once per day at 21:30 UTC (4:30 PM ET, after market close)
    """
    disabled = os.getenv("DISABLE_SCHEDULED_PIPELINE", "").lower() in ("1", "true", "yes")
    if disabled:
        print("[Scheduler] All scheduled jobs disabled via DISABLE_SCHEDULED_PIPELINE")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        market_interval = int(os.getenv("MARKET_REFRESH_MINUTES", "15"))
        news_interval = int(os.getenv("NEWS_PIPELINE_MINUTES", "60"))
        snapshot_hour = int(os.getenv("DAILY_SNAPSHOT_HOUR", "21"))
        snapshot_minute = int(os.getenv("DAILY_SNAPSHOT_MINUTE", "30"))

        scheduler = BackgroundScheduler()

        scheduler.add_job(_scheduled_market_refresh, "interval", minutes=market_interval,
                          id="market_refresh", name="Market data + F&G (15min)")
        scheduler.add_job(_scheduled_news_pipeline, "interval", minutes=news_interval,
                          id="news_pipeline", name="News pipeline (1hr)")
        scheduler.add_job(_scheduled_daily_snapshot, "cron", hour=snapshot_hour, minute=snapshot_minute,
                          id="daily_snapshot", name="Daily ML snapshot (after market close)")

        scheduler.start()
        print(f"[Scheduler] Market trackers: every {market_interval} min")
        print(f"[Scheduler] News pipeline: every {news_interval} min")
        print(f"[Scheduler] Daily snapshot: {snapshot_hour:02d}:{snapshot_minute:02d} UTC")
    except Exception as e:
        print(f"[Scheduler] Failed to start: {e}")


# On startup: populate market cache + run news pipeline immediately
_refresh_market_cache()
_scheduled_news_pipeline()
_start_schedulers()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true", host="0.0.0.0", port=int(os.getenv("PORT", 5001)))
