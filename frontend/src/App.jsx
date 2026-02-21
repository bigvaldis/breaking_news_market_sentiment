import { useState, useEffect } from 'react'
import './App.css'
import Sp500Chart from './Sp500Chart.jsx'
import GoldChart from './GoldChart.jsx'
import VixChart from './VixChart.jsx'

const API = '/api'

function useMarkets() {
  const [markets, setMarkets] = useState({ sp500_data: [], gold_data: [], vix_data: [], btc_data: [] })
  useEffect(() => {
    const load = () => {
      fetch(`${API}/markets`, { cache: 'no-store' })
        .then((r) => r.json())
        .then((j) => setMarkets({
          sp500_data: j.sp500_data || [],
          gold_data: j.gold_data || [],
          vix_data: j.vix_data || [],
          btc_data: j.btc_data || [],
        }))
    }
    load()
    const id = setInterval(load, 15 * 60 * 1000)
    return () => clearInterval(id)
  }, [])
  return markets
}

function SentimentGauge({ summary }) {
  if (!summary || summary.error) return null
  const score = summary.overall_score ?? 0
  const label = (summary.sentiment_label || 'neutral').toUpperCase()
  const displayLabel = label === 'POSITIVE' ? 'BULLISH' : label === 'NEGATIVE' ? 'BEARISH' : 'NEUTRAL'
  const pct = Math.round((score + 1) / 2 * 100)
  const color = score >= 0.05 ? '#22c55e' : score <= -0.05 ? '#ef4444' : '#eab308'

  return (
    <div className="gauge-card">
      <h3>Market Sentiment</h3>
      <div className="gauge-bullish-wrap">
        <div className="gauge-track gradient-track">
          <div className="gauge-needle" style={{ left: `${pct}%`, borderColor: color }} />
        </div>
        <div className="gauge-bullish-value">
          <span className="sentiment-label" style={{ color }}>{displayLabel}</span>
          <span className="gauge-value" style={{ color }}>{pct}/100</span>
        </div>
      </div>
      <p className="aggregated-label">Aggregated Sentiment Score</p>
      <div className="stats-row">
        <span className="stat positive">{summary.positive_pct}% positive</span>
        <span className="stat neutral">{summary.neutral_pct}% neutral</span>
        <span className="stat negative">{summary.negative_pct}% negative</span>
      </div>
    </div>
  )
}

function TrendBadge({ trend }) {
  if (!trend) return null
  const cls = trend === 'improving' ? 'trend-up' : trend === 'declining' ? 'trend-down' : 'trend-stable'
  return <span className={`trend-badge ${cls}`}>{trend}</span>
}

function formatTimeAgo(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now - d
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  if (diffMins < 60) return `${diffMins} min ago`
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
  return d.toLocaleDateString()
}

function NewsList({ news }) {
  if (!news?.length) return <p className="empty">No news yet. Run the pipeline to fetch articles.</p>
  const sentimentEmoji = (label) => {
    if (label === 'positive') return '😊'
    if (label === 'negative') return '☹'
    return '😐'
  }
  return (
    <div className="news-table-wrap">
      <table className="news-table">
        <thead>
          <tr>
            <th>Headline</th>
            <th>Source</th>
            <th>Time</th>
            <th>Sentiment</th>
          </tr>
        </thead>
        <tbody>
          {news.slice(0, 30).map((article, i) => (
            <tr key={i}>
              <td>
                <a href={article.url} target="_blank" rel="noopener noreferrer" className="news-title">
                  {article.title}
                </a>
              </td>
              <td className="news-source-cell">{article.source}</td>
              <td className="news-time-cell">{formatTimeAgo(article.published_at)}</td>
              <td>
                <span className={`sentiment-badge ${article.sentiment_label || 'neutral'}`}>
                  {(article.sentiment_label || 'neutral').charAt(0).toUpperCase() + (article.sentiment_label || 'neutral').slice(1)}
                  {' '}{sentimentEmoji(article.sentiment_label || 'neutral')}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function SentimentYesterdayVsToday({ history }) {
  if (!history?.length) return null

  const byDate = {}
  for (const h of history) {
    const ts = h.timestamp
    const score = h.overall_score
    if (ts == null || score == null) continue
    const d = new Date(ts).toISOString().slice(0, 10)
    if (!byDate[d]) byDate[d] = []
    byDate[d].push(score)
  }
  const dates = Object.keys(byDate).sort()
  const avg = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length
  const todayStr = dates[dates.length - 1]
  const yesterdayStr = dates.length >= 2 ? dates[dates.length - 2] : null
  const todayScore = todayStr && byDate[todayStr] ? avg(byDate[todayStr]) : null
  const yesterdayScore = yesterdayStr && byDate[yesterdayStr] ? avg(byDate[yesterdayStr]) : null

  if (todayScore == null && yesterdayScore == null) return null

  const toLabel = (s) => (s >= 0.05 ? 'Positive' : s <= -0.05 ? 'Negative' : 'Neutral')
  const toColor = (s) => (s >= 0.05 ? '#86efac' : s <= -0.05 ? '#fca5a5' : '#bef264')
  const fmt = (s) => (s != null ? s.toFixed(2) : '—')

  return (
    <div className="chart-card sentiment-compare-card">
      <h3>Sentiment Yesterday vs Today</h3>
      <div className="sentiment-compare">
        <div className="sentiment-day">
          <span className="day-label">Yesterday</span>
          <span className="day-score" style={{ color: toColor(yesterdayScore) }}>{fmt(yesterdayScore)}</span>
          <span className="day-sentiment">{toLabel(yesterdayScore)}</span>
        </div>
        <div className="sentiment-vs">vs</div>
        <div className="sentiment-day">
          <span className="day-label">Today</span>
          <span className="day-score" style={{ color: toColor(todayScore) }}>{fmt(todayScore)}</span>
          <span className="day-sentiment">{toLabel(todayScore)}</span>
        </div>
      </div>
    </div>
  )
}

function FearGreedCard({ fearGreed }) {
  if (!fearGreed || fearGreed.error) {
    return (
      <div className="correlation-card fear-greed-card">
        <h3>Fear & Greed Index</h3>
        <p className="correlation-empty">
          {fearGreed?.error ? `Unable to fetch: ${fearGreed.error}` : 'Loading…'}
        </p>
      </div>
    )
  }

  const value = fearGreed.value ?? 0
  const classification = fearGreed.classification || 'Unknown'
  const pct = Math.min(100, Math.max(0, value))
  const hue = (pct / 100) * 120
  const color = `hsl(${hue}, 65%, 48%)`
  const needleAngleDeg = 180 - 180 * (pct / 100)
  const needleRad = (needleAngleDeg * Math.PI) / 180
  const cx = 60
  const cy = 28
  const r = 44
  const needleLen = 36
  const needleX = cx + needleLen * Math.cos(needleRad)
  const needleY = cy - needleLen * Math.sin(needleRad)
  const arcLen = Math.PI * r
  const filledLen = arcLen * (pct / 100)
  const gapLen = arcLen - filledLen

  return (
    <div className="correlation-card fear-greed-card">
      <h3>Fear & Greed Index</h3>
      <div className="fear-greed-gauge-wrap">
        <svg viewBox="0 0 120 85" className="fear-greed-svg">
          <defs>
            <linearGradient id="fearGreedGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#ef4444" />
              <stop offset="20%" stopColor="#f97316" />
              <stop offset="40%" stopColor="#eab308" />
              <stop offset="60%" stopColor="#84cc16" />
              <stop offset="80%" stopColor="#4ade80" />
              <stop offset="100%" stopColor="#22c55e" />
            </linearGradient>
            <filter id="needleShadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="1" stdDeviation="1" floodOpacity="0.15" />
            </filter>
          </defs>
          <path
            d="M 14 72 A 44 44 0 0 1 106 72"
            fill="none"
            stroke="#e2e8f0"
            strokeWidth="12"
            strokeLinecap="round"
          />
          <path
            d="M 14 72 A 44 44 0 0 1 106 72"
            fill="none"
            stroke="url(#fearGreedGradient)"
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${filledLen} ${gapLen}`}
            style={{ transition: 'stroke-dasharray 0.5s ease' }}
          />
          <line
            x1={cx}
            y1={cy}
            x2={needleX}
            y2={needleY}
            stroke={color}
            strokeWidth="2.5"
            strokeLinecap="round"
            filter="url(#needleShadow)"
          />
          <circle cx={cx} cy={cy} r="5" fill="white" stroke={color} strokeWidth="2" />
        </svg>
        <div className="fear-greed-value-block">
          <span className="fear-greed-value" style={{ color }}>{value}</span>
          <span className="fear-greed-max">/ 100</span>
        </div>
        <p className="fear-greed-classification" style={{ color }}>{classification}</p>
        <div className="fear-greed-labels">
          <span>Extreme Fear</span>
          <span>Extreme Greed</span>
        </div>
      </div>
      <p className="fear-greed-source">Alternative.me · Crypto</p>
    </div>
  )
}

function BtcTrackerCard({ btcData }) {
  if (!btcData?.length) {
    return (
      <div className="correlation-card btc-tracker-card">
        <h3>BTC Tracker</h3>
        <p className="correlation-empty">Loading…</p>
      </div>
    )
  }

  const latest = btcData[btcData.length - 1]
  const prev = btcData[btcData.length - 2]
  const price = latest?.close ?? 0
  const prevPrice = prev?.close ?? price
  const changePct = prevPrice ? ((price - prevPrice) / prevPrice) * 100 : 0
  const isUp = changePct >= 0

  const fmt = (n) => {
    if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`
    if (n >= 1e3) return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0, minimumFractionDigits: 0 })}`
    return `$${n.toFixed(2)}`
  }

  return (
    <div className="correlation-card btc-tracker-card">
      <h3>
        <span className="btc-logo">₿</span> BTC Tracker
      </h3>
      <p className="btc-price">{fmt(price)}</p>
      <p className={`btc-change ${isUp ? 'up' : 'down'}`}>
        {isUp ? '▲' : '▼'} {Math.abs(changePct).toFixed(2)}% (24h)
      </p>
      <p className="btc-label">Bitcoin (BTC-USD)</p>
    </div>
  )
}


export default function App() {
  const [summary, setSummary] = useState(null)
  const [news, setNews] = useState([])
  const [history, setHistory] = useState([])
  const [fearGreed, setFearGreed] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [apiConnected, setApiConnected] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)
  const markets = useMarkets()

  const fetchNews = async () => {
    try {
      const res = await fetch(`${API}/news`)
      const data = await res.json()
      setNews(data.news || [])
    } catch {
      /* ignore */
    }
  }

  const fetchData = async () => {
    const healthRes = await fetch(`${API}/health`)
    if (!healthRes.ok) throw new Error('Health check failed')
    setApiConnected(true)
    setError(null)

    const [sumRes, newsRes, histRes, fgRes] = await Promise.all([
      fetch(`${API}/sentiment-summary`),
      fetch(`${API}/news`),
      fetch(`${API}/sentiment-history`),
      fetch(`${API}/fear-greed`),
    ])
    const sum = await sumRes.json()
    const newsData = await newsRes.json()
    const histData = await histRes.json()
    const fgData = await fgRes.json()
    setSummary(sum)
    setNews(newsData.news || [])
    setHistory(histData.history || [])
    setFearGreed(fgData)
    setLastUpdated(new Date())
  }

  const runPipeline = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/pipeline/run`, { method: 'POST' })
      const data = await res.json()
      if (data.error) {
        setError(data.error === 'no_news' ? 'No news fetched. RSS feeds may be temporarily unavailable.' : data.message || data.error)
      } else {
        setSummary(data)
        await fetchData()
      }
    } catch (e) {
      setError('Could not run pipeline. Is the Flask server running?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    const tryConnect = async (attempt = 0) => {
      if (cancelled) return
      const isDeployed = !window.location.hostname.match(/^localhost|127\.0\.0\.1$/)
      const maxAttempts = isDeployed ? 15 : 3
      try {
        await fetchData()
        if (cancelled) return
        return
      } catch (e) {
        if (cancelled) return
        setApiConnected(false)
        if (attempt < maxAttempts - 1) {
          setError(isDeployed
            ? `Starting up... retrying in a few seconds (${attempt + 1}/${maxAttempts})`
            : 'Could not reach API. Start the backend.')
          setTimeout(() => tryConnect(attempt + 1), 5000)
        } else {
          setError(isDeployed
            ? 'Service unavailable. Click Retry or check Render dashboard logs.'
            : 'Could not reach API. Start the backend: ./start.sh or run python api/app.py')
        }
      }
    }
    tryConnect()
    return () => { cancelled = true }
  }, [])

  // Auto-fetch news on first load when feed is empty
  useEffect(() => {
    if (apiConnected && news.length === 0 && !loading && !error) {
      runPipeline()
    }
  }, [apiConnected, news.length])

  // News auto-refresh every 1 hour
  useEffect(() => {
    const id = setInterval(fetchNews, 60 * 60 * 1000)
    return () => clearInterval(id)
  }, [])

  // Retry connection when disconnected
  useEffect(() => {
    if (!apiConnected && !loading) {
      const id = setInterval(() => fetchData().catch(() => {}), 5000)
      return () => clearInterval(id)
    }
  }, [apiConnected, loading])

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <h1>News & Market Sentiment Analysis</h1>
          <p className="subtitle">Financial market sentiment from news</p>
        </div>
        <div className="header-right">
          <div className={`api-status ${apiConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot" />
            {apiConnected ? 'API connected' : 'API disconnected'}
          </div>
          <button
            className="run-btn"
            onClick={runPipeline}
            disabled={loading}
          >
            {loading ? 'Fetching & analyzing…' : 'Fetch Latest News'}
          </button>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          {error}
          <button
            className="retry-btn"
            onClick={async () => {
              setError(null)
              try {
                await fetchData()
              } catch {
                setApiConnected(false)
                setError('Still unavailable. Check Render logs or try again later.')
              }
            }}
          >
            Retry
          </button>
        </div>
      )}

      <main className="main">
        <section className="summary-section">
          <SentimentGauge summary={summary} />
          {summary && !summary.error && (
            <div className="trend-card">
              <h3>Trend</h3>
              <TrendBadge trend={summary.trend} />
              <p className="article-count">{summary.article_count} articles analyzed</p>
            </div>
          )}
        </section>

        <SentimentYesterdayVsToday history={history} />

        <section className="correlation-section">
          <div className="fear-greed-btc-row">
            <FearGreedCard fearGreed={fearGreed} />
            <BtcTrackerCard btcData={markets.btc_data} />
          </div>
          <p className="refresh-hint">Trackers refresh every 15 min · News every 1 hr</p>
          <div className="charts-row charts-row-3">
            <Sp500Chart data={markets.sp500_data} />
            <GoldChart data={markets.gold_data} />
            <VixChart data={markets.vix_data} />
          </div>
        </section>

        <section className="news-section">
          <h2>Latest News</h2>
          <NewsList news={news} />
        </section>
      </main>

      <footer className="footer">
        {lastUpdated && (
          <p className="last-updated">Last Updated: {lastUpdated.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}</p>
        )}
        <p className="developer-credit">
          Built by{' '}
          <a href="https://www.linkedin.com/in/shaonbiswas/" target="_blank" rel="noopener noreferrer" className="developer-link">
            Shaon Biswas
          </a>
        </p>
      </footer>
    </div>
  )
}
