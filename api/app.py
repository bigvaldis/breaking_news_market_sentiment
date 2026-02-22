"""Flask API for News & Market Sentiment Analysis."""

import math
import os
from pathlib import Path

import pandas as pd

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Add project root to path
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

# Use DATA_DIR env var if set (e.g. Render disk mount path). Default: project/data
_data_dir = os.getenv("DATA_DIR")
DATA_DIR = Path(_data_dir) if _data_dir else Path(__file__).resolve().parent.parent / "data"
app = Flask(__name__)
CORS(app)


def run_pipeline(use_news_api: bool = False) -> dict:
    """Run full pipeline and return summary."""
    if use_news_api and os.getenv("NEWSAPI_KEY"):
        df = fetch_news_api(os.getenv("NEWSAPI_KEY"))
        if df.empty:
            df = fetch_all_news()
    else:
        df = fetch_all_news()

    if df.empty:
        return {"error": "no_news"}

    # Filter to financial/political news, prefer CNBC, Bloomberg, CNN, BBC, ABC
    # Jim Cramer and Trump-related content get higher priority
    df = filter_and_rank_news(df)
    if df.empty:
        return {"error": "no_news", "message": "No financial or political news matched filters"}

    df = analyze_sentiment_vader(df)
    summary = get_market_sentiment_summary(df)
    save_news(df, DATA_DIR)
    append_sentiment_summary(summary, DATA_DIR)

    # Collect daily snapshot for data science (sentiment + all market indicators)
    try:
        collect_daily_snapshot(summary, DATA_DIR, news_df=df)
    except Exception as e:
        print(f"Daily tracker snapshot failed (non-fatal): {e}")

    history = load_sentiment_history(DATA_DIR)
    trend = get_sentiment_trend(history)
    return {**summary, "trend": trend["trend"], "recent_avg": trend["recent_avg"]}


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
    """Get latest news from archive."""
    df = load_news(DATA_DIR)
    df = df.sort_values("published_at", ascending=False).head(100)
    records = df_to_news_list(df)
    records = [r for r in records if r.get("title")]
    for r in records:
        if not r.get("news_type"):
            r["news_type"] = classify_news_type(r.get("title", ""), r.get("summary", ""), r.get("source", ""))
    return jsonify({"news": _clean_for_json(records)})


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
    """Crypto Fear & Greed Index from Alternative.me."""
    result = fetch_fear_greed()
    resp = jsonify(result)
    resp.headers["Cache-Control"] = "no-store, no-cache, max-age=300"
    return resp


@app.route("/api/wall-street-fear-greed")
def get_wall_street_fear_greed():
    """Wall Street (CNN) Fear & Greed Index via RapidAPI. Requires RAPIDAPI_KEY."""
    result = fetch_wall_street_fear_greed()
    resp = jsonify(result)
    resp.headers["Cache-Control"] = "no-store, no-cache, max-age=300"
    return resp


@app.route("/api/markets")
def get_markets():
    """S&P 500, Gold, VIX, and BTC OHLC in one response. Fetches sequentially to avoid yfinance mix-up."""
    sp500_df = fetch_sp500_history(days=90)
    gold_df = fetch_gold_history(days=90)
    vix_df = fetch_vix_history(days=90)
    btc_df = fetch_btc_history(days=90)
    resp = jsonify({
        "sp500_data": _ohlc_to_list(sp500_df),
        "gold_data": _ohlc_to_list(gold_df),
        "vix_data": _ohlc_to_list(vix_df),
        "btc_data": _ohlc_to_list(btc_df),
    })
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@app.route("/api/markets/sp500")
def get_sp500():
    """S&P 500 only - separate endpoint to avoid data mix-up."""
    df = fetch_sp500_history(days=90)
    resp = jsonify({"asset": "sp500", "data": _ohlc_to_list(df)})
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@app.route("/api/markets/gold")
def get_gold():
    """Gold only - separate endpoint to avoid data mix-up."""
    df = fetch_gold_history(days=90)
    resp = jsonify({"asset": "gold", "data": _ohlc_to_list(df)})
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@app.route("/api/markets/vix")
def get_vix():
    """VIX only - separate endpoint to avoid data mix-up."""
    df = fetch_vix_history(days=90)
    resp = jsonify({"asset": "vix", "data": _ohlc_to_list(df)})
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@app.route("/api/health")
def health():
    """Health check."""
    return jsonify({"status": "ok"})


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


def _run_scheduled_pipeline():
    """Run pipeline once per day. File lock ensures only one process runs (Gunicorn multi-worker)."""
    if os.getenv("DISABLE_SCHEDULED_PIPELINE", "").lower() in ("1", "true", "yes"):
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = DATA_DIR / ".pipeline_schedule.lock"
    try:
        from filelock import FileLock
        lock = FileLock(lock_path, timeout=150)
        with lock:
            result = run_pipeline(use_news_api=True)
            print(f"[Scheduled pipeline] {result.get('article_count', 0)} articles, score={result.get('overall_score')}")
    except Exception as e:
        print(f"[Scheduled pipeline] Failed: {e}")


def _start_scheduler():
    """Start daily pipeline scheduler (2 PM UTC). No extra cost — runs on same web service."""
    if os.getenv("DISABLE_SCHEDULED_PIPELINE", "").lower() in ("1", "true", "yes"):
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        hour = int(os.getenv("PIPELINE_SCHEDULE_HOUR", "14"))
        minute = int(os.getenv("PIPELINE_SCHEDULE_MINUTE", "0"))
        scheduler = BackgroundScheduler()
        scheduler.add_job(_run_scheduled_pipeline, "cron", hour=hour, minute=minute)
        scheduler.start()
        print(f"[Scheduler] Daily pipeline at {hour:02d}:{minute:02d} UTC")
    except Exception as e:
        print(f"[Scheduler] Failed to start: {e}")


_start_scheduler()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true", host="0.0.0.0", port=int(os.getenv("PORT", 5001)))
