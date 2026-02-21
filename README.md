# Breaking News & Financial Sentiment Analysis

Extract breaking financial news from multiple sources and track market sentiment over time.

## Features

- **News extraction** from RSS feeds (Bloomberg, CNBC, Dow Jones, Yahoo Finance, Reuters) — no API key required
- **S&P 500 correlation** — correlates news sentiment with S&P 500 returns (same-day and 1-day lag)
- **Optional NewsAPI** integration for more sources (add `NEWSAPI_KEY` to `.env`)
- **Sentiment analysis** using VADER (fast, works on CPU)
- **Historical tracking** — sentiment scores and trends saved to `data/`
- **Trend detection** — improving, declining, or stable market sentiment

## Setup

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Optional: Copy .env.example to .env and add API keys
cp .env.example .env
```

## Usage

### Run the full pipeline

```bash
python main.py
```

This will:
1. Fetch breaking news from RSS feeds (and NewsAPI if configured)
2. Analyze sentiment of each article
3. Save news to `data/news_archive.csv`
4. Append sentiment summary to `data/sentiment_history.json`
5. Print a market sentiment report

### Use as a module

```python
from src.news_extractor import fetch_all_news
from src.sentiment_analyzer import analyze_sentiment_vader, get_market_sentiment_summary
from src.sentiment_tracker import save_news, append_sentiment_summary, load_sentiment_history

# Fetch and analyze
df = fetch_all_news()
df = analyze_sentiment_vader(df)
summary = get_market_sentiment_summary(df)
print(summary)  # {'overall_score': 0.12, 'sentiment_label': 'positive', ...}
```

## Web app (Flask + React)

Run the full-stack app with a dashboard. Requires [Node.js](https://nodejs.org/) for the React frontend.

**Option A – Start both servers:**
```bash
chmod +x start.sh
./start.sh
```

**Option B – Separate terminals:**

Terminal 1 – Flask API (must run first, uses port 5001 to avoid macOS AirPlay conflict):
```bash
source venv/bin/activate
python api/app.py
```

Terminal 2 – React frontend:
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The header shows **API connected** when Flask is running. Click **Fetch Latest News** to run the pipeline.

## Project structure

```
├── main.py              # CLI entry point
├── api/
│   └── app.py           # Flask API
├── frontend/            # React (Vite) dashboard
├── data/                # Created on first run
└── src/
    ├── news_extractor.py
    ├── sentiment_analyzer.py
    └── sentiment_tracker.py
```

## Deployment

**Render (one-click):** Push to GitHub → [Render](https://render.com) → New → Blueprint → Connect repo → Deploy. Uses `render.yaml` + `Dockerfile`.

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for other options (Railway, Docker, VPS).

Quick local production run:
```bash
./deploy.sh
```

## Customization

- **Add RSS feeds**: Edit `RSS_FEEDS` in `src/news_extractor.py`
- **Use NewsAPI**: Get a free key at [newsapi.org](https://newsapi.org) and add to `.env`
- **FinBERT** (financial-specific): Add `finbert` to requirements and implement in `sentiment_analyzer.py` for domain-tuned sentiment

## Data outputs

| File | Description |
|------|-------------|
| `news_archive.csv` | All fetched articles with sentiment scores |
| `sentiment_history.json` | Timestamped sentiment snapshots for trend analysis |
