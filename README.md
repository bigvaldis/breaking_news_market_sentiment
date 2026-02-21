# Breaking News & Market Sentiment Analysis

A full-stack financial sentiment dashboard that aggregates breaking news from multiple sources, analyzes market sentiment using NLP, and correlates it with live market data including S&P 500, Gold, VIX, and Bitcoin.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://reactjs.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com/)

---

## Overview

This application provides real-time insights into financial market sentiment by:

- **Aggregating** breaking news from Bloomberg, CNBC, Dow Jones, Yahoo Finance, and Reuters
- **Analyzing** sentiment using VADER (Valence Aware Dictionary and sEntiment Reasoner)
- **Tracking** sentiment trends over time with historical snapshots
- **Visualizing** market data via interactive candlestick charts (S&P 500, Gold, VIX)
- **Monitoring** the Fear & Greed Index and Bitcoin price

---

## Features

| Feature | Description |
|---------|-------------|
| **News Extraction** | RSS feeds from major financial outlets — no API key required for core sources |
| **Sentiment Analysis** | VADER-based analysis with positive/negative/neutral classification |
| **Market Charts** | S&P 500, Gold (spot), and VIX candlestick charts with 90-day history |
| **Fear & Greed Index** | Crypto market sentiment gauge (Alternative.me) with fuel-gauge visualization |
| **BTC Tracker** | Real-time Bitcoin price and 1-day change |
| **Trend Detection** | Improving, declining, or stable sentiment over time |
| **NewsAPI Integration** | Optional expansion with additional sources (requires API key) |

---

## Tech Stack

- **Backend:** Python 3.10+, Flask, pandas, yfinance, VADER
- **Frontend:** React 18, Vite, lightweight-charts
- **Data:** RSS feeds, Yahoo Finance, Alternative.me API

---

## Prerequisites

- Python 3.10 or higher
- Node.js 18+ (for the web dashboard)
- pip and npm

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ShaonINT/breaking_news_market_sentiment.git
cd breaking_news_market_sentiment
```

### 2. Backend setup

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend setup

```bash
cd frontend
npm install
cd ..
```

### 4. Environment (optional)

```bash
cp .env.example .env
# Add NEWSAPI_KEY to .env for additional news sources
```

---

## Usage

### Web application (recommended)

Start both the API and frontend:

```bash
./start.sh
```

Then open [http://localhost:3000](http://localhost:3000).

**Manual start (two terminals):**

```bash
# Terminal 1 — Flask API (port 5001)
source venv/bin/activate
python api/app.py

# Terminal 2 — React frontend
cd frontend && npm run dev
```

### CLI pipeline

Run the news fetch and sentiment analysis pipeline without the UI:

```bash
python main.py
```

---

## Project Structure

```
├── api/
│   └── app.py              # Flask REST API
├── frontend/               # React (Vite) dashboard
│   ├── src/
│   │   ├── App.jsx         # Main dashboard
│   │   ├── Sp500Chart.jsx  # S&P 500 candlestick
│   │   ├── GoldChart.jsx   # Gold candlestick
│   │   ├── VixChart.jsx    # VIX candlestick
│   │   └── ...
│   └── package.json
├── src/
│   ├── news_extractor.py   # RSS & NewsAPI fetching
│   ├── sentiment_analyzer.py
│   ├── sentiment_tracker.py
│   ├── market_data.py      # yfinance (S&P, Gold, VIX, BTC)
│   └── fear_greed.py       # Alternative.me Fear & Greed API
├── data/                   # Generated at runtime
│   ├── news_archive.csv
│   └── sentiment_history.json
├── main.py                 # CLI entry point
├── requirements.txt
├── render.yaml             # Render deployment config
├── Dockerfile
└── DEPLOYMENT.md           # Deployment guide
```

---

## Deployment

### Render (one-click)

1. Push to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**
3. Connect your repository
4. Render detects `render.yaml` and deploys automatically

### Other options

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for Railway, Docker, and VPS deployment instructions.

### Local production build

```bash
./deploy.sh
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/news` | GET | Latest news archive |
| `/api/sentiment-summary` | GET | Current sentiment summary |
| `/api/sentiment-history` | GET | Historical sentiment data |
| `/api/fear-greed` | GET | Fear & Greed Index |
| `/api/markets` | GET | S&P 500, Gold, VIX, BTC OHLC |
| `/api/pipeline/run` | POST | Trigger news fetch & analysis |

---

## Configuration

| Variable | Description |
|----------|-------------|
| `PORT` | Server port (default: 5001) |
| `FLASK_DEBUG` | Set to `true` for debug mode |

### API Keys & Data Sources

| Key | Required | Source | Description |
|-----|----------|--------|-------------|
| `NEWSAPI_KEY` | Optional | [newsapi.org](https://newsapi.org) → Get API Key | Additional news sources. Free tier: 100 requests/day. |
| — | — | RSS feeds (Bloomberg, CNBC, Reuters, etc.) | No key needed |
| — | — | [Yahoo Finance](https://finance.yahoo.com) (via yfinance) | No key needed — S&P 500, Gold, VIX, BTC |
| — | — | [Alternative.me](https://alternative.me/crypto/fear-and-greed-index/) | No key needed — Fear & Greed Index |

Add keys to `.env`:

```bash
cp .env.example .env
# Edit .env and add: NEWSAPI_KEY=your_key_here
```

---

## Data Outputs

| File | Description |
|------|-------------|
| `data/news_archive.csv` | Fetched articles with sentiment scores |
| `data/sentiment_history.json` | Timestamped sentiment snapshots |

---

## License

MIT

---

## Author

**Shaon Biswas**

Repository: [github.com/ShaonINT/breaking_news_market_sentiment](https://github.com/ShaonINT/breaking_news_market_sentiment)
