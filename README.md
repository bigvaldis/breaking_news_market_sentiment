# Breaking News & Market Sentiment Analysis

> A full-stack financial intelligence dashboard that aggregates breaking news from major financial outlets, performs real-time NLP sentiment analysis, and visualises live market data across S&P 500, Gold, VIX, and Bitcoin.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5.x-646cff.svg)](https://vitejs.dev/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ed.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-46e3b7.svg)](https://news-sentiment.imshaon.com/)

**🔗 Live Demo:** [news-sentiment.imshaon.com](https://news-sentiment.imshaon.com/)

---

## Overview

This project bridges financial news aggregation and market sentiment intelligence. It continuously pulls articles from Bloomberg, CNBC, Reuters, Yahoo Finance, and Dow Jones via RSS (no API key required), processes them through a VADER NLP sentiment pipeline, and surfaces actionable signals — bullish, bearish, or neutral — alongside live market charts and a real-time Fear & Greed Index.

Built as a full-stack application with a Flask REST API backend and a React 18 frontend, the system is containerised with Docker and deployed to Render via `render.yaml` blueprint.

---

## Screenshots

| Dashboard |
|-----------|
| ![Dashboard](screenshots/dashboard.png) |

---

## Features

- **News aggregation** — RSS feeds from Bloomberg, CNBC, Reuters, Yahoo Finance, and Dow Jones with zero API dependency
- **NLP sentiment analysis** — VADER-based positive / negative / neutral classification with confidence scoring
- **Trend detection** — Automatically classifies sentiment trajectory as improving, declining, or stable over time
- **Interactive market charts** — Candlestick charts for S&P 500, Gold, and VIX with 90-day historical data powered by yfinance
- **Fear & Greed Index** — Live crypto market sentiment gauge via Alternative.me API
- **BTC tracker** — Real-time Bitcoin price with 24-hour change indicator
- **Optional NewsAPI integration** — Expand news sources with a free NewsAPI key
- **REST API** — Clean, documented endpoints for programmatic access to all data

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.10+, Flask 3.0 |
| NLP | VADER (vaderSentiment) |
| Market Data | yfinance, Alternative.me API |
| News Ingestion | feedparser (RSS), NewsAPI (optional) |
| Frontend | React 18, Vite, lightweight-charts |
| Styling | CSS |
| Containerisation | Docker |
| Deployment | Render (render.yaml blueprint) |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    React Frontend                     │
│   App.jsx → Sp500Chart / GoldChart / VixChart        │
└───────────────────────┬──────────────────────────────┘
                        │ HTTP (REST API)
┌───────────────────────▼──────────────────────────────┐
│                   Flask REST API                     │
│                   api/app.py                          │
└───┬───────────────────┬──────────────────────────────┘
    │                   │
┌───▼───────┐   ┌───────▼──────────────────────────────┐
│  src/     │   │  External Data Sources               │
│  news_    │   │  RSS: Bloomberg, CNBC, Reuters,      │
│  extractor│   │  Yahoo Finance, Dow Jones            │
│  .py      │   │  Market: yfinance (S&P500, Gold, VIX)│
│           │   │  Crypto: Alternative.me Fear & Greed │
│  sentiment│   └──────────────────────────────────────┘
│  _analyzer│
│  .py      │
│           │
│  market_  │
│  data.py  │
│           │
│  fear_    │
│  greed.py │
└───────────┘
```

---

## Project Structure

```
breaking_news_market_sentiment/
│
├── api/
│   └── app.py                  # Flask REST API — all endpoints
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main dashboard component
│   │   ├── Sp500Chart.jsx      # S&P 500 candlestick chart
│   │   ├── GoldChart.jsx       # Gold candlestick chart
│   │   └── VixChart.jsx        # VIX volatility chart
│   └── package.json
│
├── src/
│   ├── news_extractor.py       # RSS feed ingestion & parsing
│   ├── sentiment_analyzer.py   # VADER NLP sentiment pipeline
│   ├── sentiment_tracker.py    # Historical sentiment tracking & trend detection
│   ├── market_data.py          # yfinance market data fetcher
│   └── fear_greed.py           # Alternative.me Fear & Greed Index
│
├── main.py                     # CLI pipeline runner
├── Dockerfile                  # Container definition
├── render.yaml                 # Render deployment blueprint
├── requirements.txt
├── .env.example
└── DEPLOYMENT.md               # Extended deployment options
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check — confirms API is running |
| `/api/news` | GET | Latest aggregated news articles |
| `/api/sentiment-summary` | GET | Current overall sentiment (bullish / bearish / neutral) |
| `/api/sentiment-history` | GET | Historical sentiment time series |
| `/api/fear-greed` | GET | Live Fear & Greed Index value and classification |
| `/api/markets` | GET | S&P 500, Gold, VIX, and BTC OHLC data |
| `/api/pipeline/run` | POST | Trigger a fresh news fetch and sentiment analysis cycle |

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
# Add NEWSAPI_KEY=your_key_here to enable additional news sources
```

### 5. Run the application

```bash
./start.sh
```

Open **http://localhost:3000** and click **Fetch Latest News** to load and analyse articles.

#### Manual startup (two terminals)

```bash
# Terminal 1 — Flask API
python api/app.py

# Terminal 2 — React dev server
cd frontend && npm run dev
```

#### Production build (single server)

```bash
cd frontend && npm run build && cd ..
python api/app.py
```

Open **http://localhost:5001**

---

## Deployment

### Render (recommended — one-click)

1. Push your fork to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**
3. Connect your repository — Render auto-detects `render.yaml`
4. Select **Free** tier → **Apply**

Your app will be live at `https://<your-service>.onrender.com`

### Docker

```bash
docker build -t breaking-news-sentiment .
docker run -p 5001:5001 -e PORT=5001 breaking-news-sentiment
```

For Koyeb, Railway, or VPS deployment, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | No | Server port (default: `5001`) |
| `NEWSAPI_KEY` | No | Free API key from [newsapi.org](https://newsapi.org) for additional news sources |

---

## Roadmap

- [ ] Upgrade sentiment engine to FinBERT (transformer-based financial NLP)
- [ ] Add per-asset sentiment tracking (e.g. sentiment correlated to S&P 500 movements)
- [ ] WebSocket support for real-time sentiment push updates
- [ ] Alert system — email / Slack notifications on extreme sentiment shifts
- [ ] Sentiment backtesting against historical price data

---

## Contributing

Contributions are welcome. Please open an issue to discuss changes before submitting a pull request.

---

## License

MIT

---

**[Shaon Biswas](https://www.linkedin.com/in/shaonbiswas/)** — [GitHub](https://github.com/ShaonINT/breaking_news_market_sentiment)

*Built with Python, Flask, React, and a passion for making financial intelligence accessible.*
