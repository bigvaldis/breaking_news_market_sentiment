"""Flask API for News & Market Sentiment Analysis."""

import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from src.news_extractor import fetch_all_news, fetch_news_api
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
from src.market_data import fetch_btc_history, fetch_gold_history, fetch_sp500_history, fetch_vix_history, _ohlc_to_list

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
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

    df = analyze_sentiment_vader(df)
    summary = get_market_sentiment_summary(df)
    save_news(df, DATA_DIR)
    append_sentiment_summary(summary, DATA_DIR)

    history = load_sentiment_history(DATA_DIR)
    trend = get_sentiment_trend(history)
    return {**summary, "trend": trend["trend"], "recent_avg": trend["recent_avg"]}


def df_to_news_list(df):
    """Convert news DataFrame to JSON-serializable list."""
    if df.empty:
        return []
    df = df.copy()
    for col in ["published_at", "fetched_at"]:
        if col in df.columns:
            df[col] = df[col].astype(str)
    return df.to_dict(orient="records")


@app.route("/api/pipeline/run", methods=["POST"])
def run_pipeline_endpoint():
    """Trigger pipeline run and return summary."""
    result = run_pipeline(use_news_api=True)
    return jsonify(result)


@app.route("/api/news")
def get_news():
    """Get latest news from archive."""
    df = load_news(DATA_DIR)
    df = df.sort_values("published_at", ascending=False).head(100)
    return jsonify({"news": df_to_news_list(df)})


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


@app.route("/api/fear-greed")
def get_fear_greed():
    """Fear & Greed Index from Alternative.me (Crypto)."""
    result = fetch_fear_greed()
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


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true", host="0.0.0.0", port=int(os.getenv("PORT", 5001)))
