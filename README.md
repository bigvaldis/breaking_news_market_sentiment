# News & Market Sentiment Analysis

> A full-stack financial intelligence dashboard that aggregates breaking news from major outlets, classifies articles by type, performs real-time NLP sentiment analysis, tracks correlations with market indicators, and collects structured data for future supervised learning models.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5.x-646cff.svg)](https://vitejs.dev/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ed.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-news--sentiment.imshaon.com-46e3b7.svg)](https://news-sentiment.imshaon.com/)

**Live Demo:** [news-sentiment.imshaon.com](https://news-sentiment.imshaon.com/)

---

## Screenshots

| Dashboard |
|-----------|
| ![Dashboard](screenshots/dashboard.png) |

---

## Overview

This project combines financial news aggregation, NLP-driven sentiment analysis, live market data, and a data collection pipeline designed for future machine learning.

Articles are pulled from 14 RSS feeds spanning Bloomberg, CNBC, CNN, BBC, ABC News, Reuters, Yahoo Finance, Dow Jones, and Trump's Truth Social. Each article is filtered for financial and political relevance, classified into one of 12 news types (Financial, Political, China, Europe, War/Military, Tariff/Trade, etc.), scored using VADER NLP on the headline+summary concatenation, and persisted to a CSV archive with its type label.

Every pipeline run also snapshots the overall and per-source sentiment alongside live market closes (S&P 500, Gold, VIX, BTC) and Fear & Greed indices, building a growing time-series dataset for correlation analysis and future supervised model training.

---

## Features

### News Intelligence
- **14 curated RSS feeds** — Bloomberg, CNBC, CNN (Top/Politics/Business), BBC (News/Business), ABC News (Top/Politics), Reuters, Yahoo Finance, Dow Jones, Trump Truth Social
- **Smart filtering** — Only financial and political news passes through; preferred sources ranked higher; Jim Cramer and Trump content boosted
- **Truth Social filter** — Trump posts filtered to only market-moving topics: tariffs, war, geopolitics, China, India, Iran, Europe, UK, Greenland, Epstein, midterms, Fed, crypto, rare earth
- **12 news type labels** — Each article classified as Financial, Political, Trump Post, War/Military, China, Europe, India, Middle East, Tariff/Trade, Crypto, Fed/Monetary, US Local, or General
- **Null headline filtering** — Articles without headlines are excluded

### Sentiment Analysis
- **VADER NLP pipeline** — Compound scoring on headline + summary concatenation for better accuracy on terse financial titles
- **Percentage breakdown** — Per-run positive / negative / neutral article distribution
- **Trend detection** — Half-split algorithm classifies sentiment trajectory as improving, declining, or stable over the last 24 snapshots
- **Persistent history** — Rolling 500-snapshot JSON sentiment history

### Market Data & Indicators
- **Candlestick charts** — Financial-grade interactive charts for S&P 500, Gold, and VIX with 90-day OHLC data
- **BTC tracker** — Real-time Bitcoin price with 24h change and 90-day OHLC history
- **Crypto Fear & Greed Index** — Live crypto market sentiment via Alternative.me (free, no API key)
- **Wall Street Fear & Greed Index** — CNN stock market sentiment via RapidAPI (optional `RAPIDAPI_KEY`)

### Correlation Matrix
- **Sentiment vs market correlation** — Heatmap showing Pearson correlation between news sentiment (overall and per source) and market indicators
- **8 time periods** — 1 Day, 3 Days, 7 Days, 15 Days, 1 Month, 1 Quarter, 6 Months, 1 Year
- **Per-source breakdown** — Separate correlations for Bloomberg, CNBC, CNN, BBC, ABC News, Trump Truth Social, etc.
- **Data collection start date** displayed in the dashboard

### Data Science Pipeline
- **Daily tracker** (`data/daily_tracker.csv`) — Each pipeline run appends: date, sentiment score/label/percentages, article count, Crypto F&G, Wall Street F&G, S&P 500 close, Gold close, VIX close, BTC close
- **Source sentiment tracker** (`data/source_sentiment.csv`) — Per-source-category average sentiment with corresponding market data for correlation computation
- **News archive** (`data/news_archive.csv`) — All articles with sentiment scores, labels, source, URL, and `news_type` classification — ready for supervised learning
- **Multi-label classification available** — `classify_news_types_multi()` returns all matching types per article for multi-label ML tasks

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.10+, Flask 3.0 |
| NLP | VADER (vaderSentiment) |
| News Classification | Regex-based multi-pattern classifier (12 types) |
| Market Data | yfinance (S&P 500, Gold, VIX, BTC) |
| Crypto Fear & Greed | Alternative.me (stdlib urllib) |
| Wall Street Fear & Greed | RapidAPI (optional) |
| News Ingestion | feedparser (14 RSS feeds), NewsAPI (optional) |
| Frontend | React 18.3, Vite 5.4 |
| Charts | lightweight-charts 4.2 |
| Containerisation | Docker |
| Deployment | Render (`render.yaml` blueprint) |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      React Frontend                           │
│  App.jsx → SentimentGauge · CorrelationMatrix · NewsList     │
│  Sp500Chart · GoldChart · VixChart · FearGreedCard · BTC     │
│  Vite 5 build → served by Flask in production                │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP REST
┌────────────────────────▼─────────────────────────────────────┐
│                    Flask REST API                              │
│                    api/app.py                                  │
│  17 routes · CORS · Cache-Control · Static serving            │
└──┬──────────┬──────────┬─────────────────────────────────────┘
   │          │          │
┌──▼──────┐ ┌▼────────┐ ┌▼─────────────────────────────────────┐
│  src/   │ │  data/   │ │  External Data Sources               │
│         │ │          │ │                                       │
│ news_   │ │ news_    │ │  RSS: Bloomberg, CNBC, CNN, BBC,     │
│ extrac  │ │ archive  │ │       ABC, Reuters, Yahoo, Dow Jones,│
│ tor.py  │ │ .csv     │ │       Trump Truth Social              │
│         │ │          │ │                                       │
│ news_   │ │ sentim.  │ │  Market: yfinance (sequential fetch) │
│ filter  │ │ history  │ │  Crypto F&G: Alternative.me          │
│ .py     │ │ .json    │ │  WS F&G: RapidAPI (optional)         │
│         │ │          │ │  NewsAPI: newsapi.org (optional)      │
│ sentim. │ │ daily_   │ └──────────────────────────────────────┘
│ analyz  │ │ tracker  │
│ er.py   │ │ .csv     │
│         │ │          │
│ sentim. │ │ source_  │
│ track   │ │ sentim.  │
│ er.py   │ │ .csv     │
│         │ └──────────┘
│ daily_  │
│ track   │
│ er.py   │
│         │
│ market_ │
│ data.py │
│         │
│ fear_   │
│ greed   │
│ .py     │
│         │
│ wall_st │
│ _fg.py  │
│         │
│ trump_  │
│ tweets  │
│ .py     │
└─────────┘
```

---

## Project Structure

```
breaking_news_market_sentiment/
│
├── api/
│   └── app.py                     # Flask REST API — 17 endpoints, pipeline orchestration, static serving
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # Dashboard: gauges, correlation matrix, news table, charts
│   │   ├── App.css                # Dark theme, responsive layout, type badges, heatmap styles
│   │   ├── Sp500Chart.jsx         # S&P 500 candlestick chart (lightweight-charts)
│   │   ├── GoldChart.jsx          # Gold candlestick chart
│   │   └── VixChart.jsx           # VIX volatility chart
│   └── package.json               # React 18.3, Vite 5.4, lightweight-charts 4.2
│
├── src/
│   ├── news_extractor.py          # 14 RSS feeds + optional NewsAPI; Trump Truth Social via RSS
│   ├── news_filter.py             # Financial/political filter, Truth Social topic filter,
│   │                              #   news_type classifier (12 types), multi-label support
│   ├── trump_tweets.py            # Optional Trump X tweets (paid API); Truth Social RSS is free
│   ├── sentiment_analyzer.py      # VADER NLP; headline+summary concat; percentage breakdown
│   ├── sentiment_tracker.py       # CSV archive; JSON history (500-cap); trend detection
│   ├── daily_tracker.py           # Daily snapshots: sentiment + all market indicators + per-source
│   │                              #   breakdown; correlation matrix computation (8 time periods)
│   ├── market_data.py             # yfinance OHLC with threading lock; Pearson correlation engine
│   ├── fear_greed.py              # Crypto Fear & Greed (Alternative.me, stdlib)
│   └── wall_street_fear_greed.py  # Wall Street Fear & Greed (RapidAPI, optional)
│
├── data/                          # Auto-created; gitignored
│   ├── news_archive.csv           # All articles with sentiment + news_type labels
│   ├── sentiment_history.json     # Rolling 500-snapshot sentiment time series
│   ├── daily_tracker.csv          # Daily sentiment vs market indicators
│   └── source_sentiment.csv       # Per-source sentiment vs market data (for correlations)
│
├── screenshots/
│   ├── dashboard.png
│   └── dashboard-hero.png
│
├── Dockerfile                     # Python 3.12 + Node.js; gunicorn with 120s timeout
├── render.yaml                    # Render blueprint (one-click deploy)
├── requirements.txt
├── start.sh                       # Dev: launches Flask + Vite concurrently
├── capture_screenshots.py         # Playwright-based screenshot capture
├── .env.example
└── .gitignore
```

---

## News Type Classification

Every article is labelled with a `news_type` for structured analysis and future ML training:

| Type | Keywords / Triggers |
|------|-------------------|
| **Trump Post** | Source is Truth Social or X |
| **China** | China, Beijing, Xi Jinping, Taiwan, Hong Kong, Huawei, TikTok |
| **Middle East** | Iran, Israel, Gaza, Saudi, OPEC, Iraq, Syria, Yemen |
| **India** | India, Modi, Mumbai, Nifty, Sensex, Rupee |
| **Europe** | EU, ECB, Germany, France, UK, Britain, eurozone, Bank of England |
| **Tariff / Trade** | Tariffs, trade war, sanctions, duties, customs |
| **War / Military** | War, attack, military, missile, NATO, conflict, nuclear |
| **Crypto** | Bitcoin, Ethereum, blockchain, DeFi, digital assets |
| **Fed / Monetary** | Federal Reserve, interest rates, Powell, FOMC, inflation, CPI |
| **Political** | Congress, Senate, elections, midterm, Epstein, executive order |
| **Financial** | Stocks, earnings, Wall Street, IPO, recession, S&P, Dow |
| **US Local** | Immigration, border, student loans, housing, FEMA |
| **General** | Articles not matching any specific category |

Region-specific types take priority over broad types (e.g. "Iran nuclear talks" classifies as Middle East, not War/Military).

---

## API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/news` | GET | Latest 100 articles with sentiment scores, labels, and `news_type` |
| `/api/sentiment-summary` | GET | Latest sentiment snapshot with trend signal and percentage breakdown |
| `/api/sentiment-history` | GET | Full sentiment time series for charting |
| `/api/pipeline/run` | POST | Trigger fresh news ingestion, classification, analysis, and data collection |

### Market & Indicators

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/markets` | GET | S&P 500, Gold, VIX, and BTC OHLC (fetched sequentially) |
| `/api/markets/sp500` | GET | S&P 500 OHLC only |
| `/api/markets/gold` | GET | Gold OHLC only |
| `/api/markets/vix` | GET | VIX data only |
| `/api/fear-greed` | GET | Crypto Fear & Greed Index |
| `/api/wall-street-fear-greed` | GET | Wall Street (CNN) Fear & Greed Index |

### Data Science

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/correlation-matrix` | GET | Sentiment vs market correlation matrix for all 8 time periods |
| `/api/correlation-matrix?period=7d` | GET | Correlation for a specific period (1d, 3d, 7d, 15d, 1m, 1q, 6m, 1y) |
| `/api/daily-tracker` | GET | Raw daily sentiment + market indicator snapshots |

> All market and fear-greed endpoints return `Cache-Control: no-store, no-cache, must-revalidate` to prevent stale financial data from CDN or browser caching.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git

### 1. Clone the repository

```bash
git clone https://github.com/ShaonINT/breaking_news_market_sentiment.git
cd breaking_news_market_sentiment
```

### 2. Backend setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend setup

```bash
cd frontend
npm install
cd ..
```

### 4. Configure environment (optional)

```bash
cp .env.example .env
# NEWSAPI_KEY=your_key        — additional news sources
# RAPIDAPI_KEY=your_key       — Wall Street Fear & Greed Index
```

### 5. Run

**Development (two servers, hot reload):**

```bash
./start.sh
# Frontend: http://localhost:3000
# API:      http://localhost:5001
```

**Production build (single server):**

```bash
cd frontend && npm run build && cd ..
python api/app.py
# Open http://localhost:5001
```

Click **Fetch Latest News** to run the pipeline, or `POST /api/pipeline/run`.

---

## Deployment

### Render (recommended)

1. Push to GitHub
2. [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**
3. Connect your repository — Render auto-detects `render.yaml`
4. Add a **Persistent Disk** (1 GB, $0.25/mo) mounted at `/app/data` to preserve collected data across deploys
5. Set environment variables in the dashboard (`NEWSAPI_KEY`, `RAPIDAPI_KEY` — both optional)

### Docker

```bash
docker build -t news-sentiment .
docker run -p 5001:5001 -v ./data:/app/data news-sentiment
```

Mount `./data` to persist the news archive, sentiment history, and daily tracker across container restarts.

---

## Data Collection for ML

The system is designed to accumulate structured data for future supervised learning:

### Collected Datasets

| File | Contents | Use Case |
|------|----------|----------|
| `news_archive.csv` | All articles: title, summary, source, URL, sentiment scores, `news_type` | Training data for text classification and sentiment prediction |
| `daily_tracker.csv` | Daily snapshots: sentiment, article count, S&P 500, Gold, VIX, BTC, Crypto F&G, WS F&G | Time-series regression: predict market moves from sentiment |
| `source_sentiment.csv` | Per-source avg sentiment + market data per day | Feature engineering: which sources predict which markets |
| `sentiment_history.json` | Rolling 500 sentiment snapshots with timestamps | Trend analysis and temporal patterns |

### Building a Supervised Model

After collecting 30+ days of data:

1. **Load daily_tracker.csv** — each row is a training sample
2. **Features**: `sentiment_score`, `positive_pct`, `negative_pct`, `crypto_fear_greed_value`, `vix_close`
3. **Target**: Next-day S&P 500 return (compute from `sp500_close` shifted by 1 day)
4. **news_type breakdown**: Aggregate per-type sentiment from `source_sentiment.csv` as additional features
5. Train a model (XGBoost, Random Forest, or LSTM for sequence data)

The `classify_news_types_multi()` function in `news_filter.py` returns all matching types per article for multi-label classification tasks.

---

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | No | Server port (default: `5001`) |
| `NEWSAPI_KEY` | No | Free key from [newsapi.org](https://newsapi.org) for expanded news coverage |
| `RAPIDAPI_KEY` | No | RapidAPI key for Wall Street (CNN) Fear & Greed; subscribe at [RapidAPI](https://rapidapi.com/rpi4gx/api/fear-and-greed-index) |
| `TWITTER_BEARER_TOKEN` | No | X API v2 bearer token for Trump tweets (paid). Truth Social RSS works without this |
| `FLASK_DEBUG` | No | Set to `true` for auto-reload during development |

---

## Key Design Decisions

**Why RSS over a commercial news API?**
RSS is free, zero-dependency, and updates in near-real-time. Every major financial publisher maintains active feeds. No registration or API key required — the system works immediately in any environment.

**Why VADER over FinBERT?**
No GPU, no model download, no inference latency. For a real-time pipeline processing dozens of articles per cycle, the speed trade-off is significant. The modular architecture allows a drop-in NLP engine replacement without changing the API contract or the frontend.

**Why headline + summary concatenation?**
Financial headlines are often terse and ambiguous in isolation ("Fed acts" could be bullish or bearish). Appending the article summary significantly improves classification accuracy without additional model complexity.

**Why regex-based news type classification?**
For the labelling task, regex patterns are deterministic, fast, and require no training data. They produce clean, consistent labels that serve as ground-truth for training a more sophisticated ML classifier later.

**Why sequential yfinance fetching?**
Concurrent requests to yfinance introduce a caching bug where multiple assets return the same data. The `/api/markets` endpoint fetches each asset sequentially behind a threading lock — slower, but reliably correct.

**Why filter Truth Social posts?**
Trump posts 20-30 times daily. Without filtering, they overwhelm the feed with birthday wishes and rally thanks. Only posts matching specific market-moving topics (tariffs, geopolitics, Fed, crypto, etc.) pass through.

---

## Roadmap

- [ ] Upgrade sentiment engine to FinBERT (transformer-based financial NLP)
- [ ] Train supervised model on accumulated daily_tracker data (XGBoost / LSTM)
- [ ] Per-news-type sentiment correlation (e.g. "China news sentiment vs S&P 500")
- [ ] Statistical significance testing on correlations (Spearman rank + p-values)
- [ ] WebSocket support for real-time sentiment push updates
- [ ] Alert system — email / Slack notifications on extreme sentiment shifts
- [ ] Sentiment backtesting against historical price data
- [ ] Auto-scheduled pipeline runs (cron-based, not just manual)

---

## Contributing

Contributions are welcome. Please open an issue to discuss changes before submitting a pull request.

---

## License

MIT © [Shaon Biswas](https://github.com/ShaonINT)

---

*Built with Python, Flask, React, and a passion for making financial intelligence accessible.*
