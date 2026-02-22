import { useState, useEffect, useRef } from 'react'
import './App.css'
import Sp500Chart from './Sp500Chart.jsx'
import GoldChart from './GoldChart.jsx'
import VixChart from './VixChart.jsx'

const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
const API = API_BASE ? `${API_BASE}/api` : '/api'

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
            <th>Type</th>
            <th>Source</th>
            <th>Time</th>
            <th>Sentiment</th>
          </tr>
        </thead>
        <tbody>
          {news.slice(0, 30).map((article, i) => (
            <tr key={i}>
              <td>
                <a href={article.url || '#'} target="_blank" rel="noopener noreferrer" className="news-title">
                  {article.title || '(No title)'}
                </a>
              </td>
              <td className="news-type-cell">
                {article.news_type && <span className={`type-badge type-${(article.news_type || '').toLowerCase().replace(/[\s\/]+/g, '-')}`}>{article.news_type}</span>}
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

function FearGreedCard({ fearGreed, title, source }) {
  if (!fearGreed || fearGreed.error) {
    const msg = fearGreed?.error === 'no_api_key'
      ? 'Set RAPIDAPI_KEY to enable'
      : fearGreed?.error
        ? `Unable to fetch: ${fearGreed.error}`
        : 'Loading…'
    return (
      <div className="correlation-card fear-greed-card">
        <h3>{title}</h3>
        <p className="correlation-empty">{msg}</p>
      </div>
    )
  }

  const value = fearGreed.value ?? 0
  const classification = fearGreed.classification || 'Unknown'
  const prevValue = fearGreed.previous_value
  const prevClassification = fearGreed.previous_classification
  const pct = Math.min(100, Math.max(0, value))

  const cx = 60
  const cy = 28
  const r = 44
  const arcLen = Math.PI * r
  const segLen = arcLen / 3

  const needleAngleDeg = 180 - 180 * (pct / 100)
  const needleRad = (needleAngleDeg * Math.PI) / 180
  const needleLen = 36
  const needleX = cx + needleLen * Math.cos(needleRad)
  const needleY = cy - needleLen * Math.sin(needleRad)

  const segmentColor = pct <= 33 ? '#f97316' : pct <= 66 ? '#eab308' : '#22c55e'

  return (
    <div className="correlation-card fear-greed-card">
      <h3>{title}</h3>
      <div className="fear-greed-gauge-wrap">
        <svg viewBox="0 0 120 85" className="fear-greed-svg">
          <defs>
            <path id="fearGreedArcPath" d="M 14 72 A 44 44 0 0 1 106 72" />
            <filter id="needleShadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="1" stdDeviation="1" floodOpacity="0.2" />
            </filter>
          </defs>
          <path
            d="M 14 72 A 44 44 0 0 1 106 72"
            fill="none"
            stroke="#f97316"
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${segLen} ${arcLen - segLen}`}
          />
          <path
            d="M 14 72 A 44 44 0 0 1 106 72"
            fill="none"
            stroke="#eab308"
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${segLen} ${segLen}`}
            strokeDashoffset={-segLen}
          />
          <path
            d="M 14 72 A 44 44 0 0 1 106 72"
            fill="none"
            stroke="#22c55e"
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${segLen} ${arcLen - segLen}`}
            strokeDashoffset={-segLen * 2}
          />
          <text className="fear-greed-arc-label">
            <textPath href="#fearGreedArcPath" startOffset="8%">FEAR</textPath>
          </text>
          <text className="fear-greed-arc-label">
            <textPath href="#fearGreedArcPath" startOffset="42%">NEUTRAL</textPath>
          </text>
          <text className="fear-greed-arc-label">
            <textPath href="#fearGreedArcPath" startOffset="75%">GREED</textPath>
          </text>
          <line
            x1={cx}
            y1={cy}
            x2={needleX}
            y2={needleY}
            stroke="#d1d5db"
            strokeWidth="2.5"
            strokeLinecap="round"
            filter="url(#needleShadow)"
          />
          <circle cx={cx} cy={cy} r="4" fill="#374151" stroke="#6b7280" strokeWidth="1" />
        </svg>
        <div className="fear-greed-value-block">
          <span className="fear-greed-value" style={{ color: segmentColor }}>{value}</span>
          <span className="fear-greed-classification-inline" style={{ color: segmentColor }}>
            ({classification.toUpperCase()})
          </span>
        </div>
        {prevValue != null && prevClassification && (
          <p className="fear-greed-previous">
            {prevClassification} Last Trading Day: {prevValue}
          </p>
        )}
      </div>
      <p className="fear-greed-source">{source}</p>
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


function CorrelationMatrix({ apiBase }) {
  const [data, setData] = useState(null)
  const [activePeriod, setActivePeriod] = useState('7d')

  useEffect(() => {
    fetch(`${apiBase}/correlation-matrix`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
  }, [apiBase])

  if (!data || !data.periods?.length) {
    const msg = data?.message || 'Run the pipeline daily to start building correlation data.'
    return (
      <div className="chart-card correlation-matrix-card">
        <h3>Sentiment vs Market Correlation</h3>
        <p className="correlation-empty">{msg}</p>
      </div>
    )
  }

  const { periods, indicators, data_start, total_days, message } = data
  const period = periods.find((p) => p.key === activePeriod) || periods[0]
  const { matrix, categories, days_available } = period

  const cellColor = (val) => {
    if (val === null || val === undefined) return { bg: 'transparent', text: 'var(--text-muted)' }
    const v = Math.max(-1, Math.min(1, val))
    if (v > 0) {
      const alpha = Math.min(v * 0.8, 0.7)
      return { bg: `rgba(34, 197, 94, ${alpha})`, text: alpha > 0.35 ? '#fff' : 'var(--text)' }
    }
    const alpha = Math.min(Math.abs(v) * 0.8, 0.7)
    return { bg: `rgba(239, 68, 68, ${alpha})`, text: alpha > 0.35 ? '#fff' : 'var(--text)' }
  }

  const hasData = categories?.length > 0

  return (
    <div className="chart-card correlation-matrix-card">
      <div className="corr-header">
        <div>
          <h3>Sentiment vs Market Correlation</h3>
          <p className="correlation-subtitle">
            {data_start && <>Collecting since <strong>{data_start}</strong> &middot; </>}
            {total_days} day(s) of data
            {days_available > 0 && <> &middot; {days_available} in selected period</>}
          </p>
          <p className="corr-markets-note">
            Correlation of average daily sentiment (overall and per source) with: S&P 500, Gold (XAU), VIX, BTC, Crypto Fear & Greed, Wall Street Fear & Greed
          </p>
        </div>
      </div>

      <div className="corr-period-tabs">
        {periods.map((p) => (
          <button
            key={p.key}
            className={`corr-period-tab ${activePeriod === p.key ? 'active' : ''}`}
            onClick={() => setActivePeriod(p.key)}
          >
            {p.label}
            {p.days_available > 0 && <span className="corr-tab-days">{p.days_available}d</span>}
          </button>
        ))}
      </div>

      {hasData ? (
        <>
          <div className="corr-matrix-wrap">
            <table className="corr-matrix-table">
              <thead>
                <tr>
                  <th className="corr-label-header">Source / Topic</th>
                  {indicators.map((ind) => (
                    <th key={ind} className="corr-indicator-header">{ind}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {categories.map((cat) => (
                  <tr key={cat} className={cat === 'Overall Sentiment' ? 'corr-overall-row' : ''}>
                    <td className="corr-category">{cat}</td>
                    {indicators.map((ind) => {
                      const val = matrix[cat]?.[ind]
                      const { bg, text } = cellColor(val)
                      return (
                        <td
                          key={ind}
                          className="corr-cell"
                          style={{ backgroundColor: bg, color: text }}
                          title={val != null ? `r = ${val.toFixed(4)}` : 'Insufficient data'}
                        >
                          {val != null ? val.toFixed(2) : '—'}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="corr-legend">
            <span className="corr-leg-pos">Green = positive correlation</span>
            <span className="corr-leg-neg">Red = negative correlation</span>
            <span className="corr-leg-none">— = not enough data</span>
          </p>
        </>
      ) : (
        <p className="correlation-empty corr-no-period-data">No data for this period yet.</p>
      )}
      {message && <p className="correlation-empty corr-note">{message}</p>}
    </div>
  )
}


export default function App() {
  const [summary, setSummary] = useState(null)
  const [news, setNews] = useState([])
  const [history, setHistory] = useState([])
  const [fearGreed, setFearGreed] = useState(null)
  const [wallStreetFearGreed, setWallStreetFearGreed] = useState(null)
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

  const fetchWithTimeout = (url, ms = 8000) => {
    const c = new AbortController()
    const t = setTimeout(() => c.abort(), ms)
    return fetch(url, { signal: c.signal }).finally(() => clearTimeout(t))
  }

  const fetchData = async () => {
    const healthRes = await fetch(`${API}/health`)
    if (!healthRes.ok) throw new Error('Health check failed')
    setApiConnected(true)
    setError(null)

    const results = await Promise.allSettled([
      fetch(`${API}/news`, { cache: 'no-store' }),
      fetch(`${API}/sentiment-summary`),
      fetch(`${API}/sentiment-history`),
      fetchWithTimeout(`${API}/fear-greed`, 6000).catch(() => ({ ok: false })),
      fetchWithTimeout(`${API}/wall-street-fear-greed`, 6000).catch(() => ({ ok: false })),
    ])
    const [newsRes, sumRes, histRes, fgRes, wsFgRes] = results.map((r) => r.status === 'fulfilled' ? r.value : null)
    const newsData = newsRes?.ok ? await newsRes.json() : { news: [] }
    const sum = sumRes?.ok ? await sumRes.json() : {}
    const histData = histRes?.ok ? await histRes.json() : { history: [] }
    const fgData = fgRes?.ok ? await fgRes.json() : {}
    const wsFgData = wsFgRes?.ok ? await wsFgRes.json() : {}
    setNews(newsData.news || [])
    setSummary(sum)
    setHistory(histData.history || [])
    setFearGreed(fgData)
    setWallStreetFearGreed(wsFgData)
    setLastUpdated(new Date())
  }

  const runPipeline = async () => {
    setLoading(true)
    setError(null)
    const isDeployed = !window.location.hostname.match(/^localhost|127\.0\.0\.1$/)
    const controller = new AbortController()
    const timeoutId = isDeployed ? setTimeout(() => controller.abort(), 100000) : null
    try {
      const res = await fetch(`${API}/pipeline/run`, { method: 'POST', signal: controller.signal })
      if (timeoutId) clearTimeout(timeoutId)
      const data = await res.json()
      if (data.error) {
        setError(data.error === 'no_news' ? 'No news fetched. RSS feeds may be temporarily unavailable.' : data.message || data.error)
      } else {
        setSummary(data)
        await fetchData()
      }
    } catch (e) {
      if (timeoutId) clearTimeout(timeoutId)
      if (e.name === 'AbortError') {
        setError(isDeployed ? 'Request timed out. The pipeline may still be running—wait a moment and Retry.' : 'Pipeline took too long. Try again.')
      } else {
        setError(isDeployed ? 'Service unavailable. If it just spun up, wait ~1 min and Retry. Otherwise check Render logs.' : 'Could not run pipeline. Is the Flask server running?')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    const tryConnect = async (attempt = 0) => {
      if (cancelled) return
      const isDeployed = !window.location.hostname.match(/^localhost|127\.0\.0\.1$/)
      const maxAttempts = isDeployed ? 24 : 3
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

  // Auto-run pipeline only when feed is empty after fetchData completes (user can also click Fetch)
  const hasTriedPipeline = useRef(false)
  useEffect(() => {
    if (!apiConnected || loading || error || news.length > 0 || hasTriedPipeline.current) return
    const t = setTimeout(() => {
      hasTriedPipeline.current = true
      runPipeline()
    }, 3000)
    return () => clearTimeout(t)
  }, [apiConnected, news.length, loading, error])

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
          <div className="error-actions">
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
            {!window.location.hostname.match(/^localhost|127\.0\.0\.1$/) && (
              <a href={`${API.replace(/\/api$/, '')}/api/health`} target="_blank" rel="noopener noreferrer" className="test-api-link">
                Test API
              </a>
            )}
          </div>
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
          <div className="fear-greed-row">
            <FearGreedCard fearGreed={fearGreed} title="Crypto Fear & Greed" source="Alternative.me · Crypto" />
            <FearGreedCard fearGreed={wallStreetFearGreed} title="Wall Street Fear & Greed" source="CNN · RapidAPI" />
          </div>
          <div className="fear-greed-btc-row">
            <BtcTrackerCard btcData={markets.btc_data} />
          </div>
          <p className="refresh-hint">Trackers refresh every 15 min · News every 1 hr</p>
          <div className="charts-row charts-row-3">
            <Sp500Chart data={markets.sp500_data} />
            <GoldChart data={markets.gold_data} />
            <VixChart data={markets.vix_data} />
          </div>
        </section>

        <section className="correlation-matrix-section">
          <CorrelationMatrix apiBase={API} />
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
