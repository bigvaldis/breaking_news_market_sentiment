import { useEffect, useRef } from 'react'
import { createChart } from 'lightweight-charts'

export default function VixChart({ data = [] }) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)

  useEffect(() => {
    if (!data?.length || !containerRef.current) return

    const hasOHLC = data[0]?.open != null && data[0]?.high != null && data[0]?.low != null
    const width = containerRef.current.clientWidth || 600

    const chart = createChart(containerRef.current, {
      layout: { background: { color: 'transparent' }, textColor: '#64748b' },
      grid: { vertLines: { color: '#e2e8f0' }, horzLines: { color: '#e2e8f0' } },
      width,
      height: 260,
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#e2e8f0' },
      rightPriceScale: { borderColor: '#e2e8f0', scaleMargins: { top: 0.1, bottom: 0.1 } },
    })
    chartRef.current = chart

    const seriesData = data.map((d) => ({
      time: d.date,
      open: hasOHLC ? d.open : d.close,
      high: hasOHLC ? d.high : d.close,
      low: hasOHLC ? d.low : d.close,
      close: d.close,
    }))

    if (hasOHLC) {
      chart.addCandlestickSeries({
        upColor: '#ef4444',
        downColor: '#10b981',
        borderDownColor: '#10b981',
        borderUpColor: '#ef4444',
        wickDownColor: '#10b981',
        wickUpColor: '#ef4444',
      }).setData(seriesData)
    } else {
      chart.addLineSeries({ color: '#64748b', lineWidth: 2 }).setData(seriesData.map((d) => ({ time: d.time, value: d.close })))
    }
    chart.timeScale().fitContent()

    const onResize = () => {
      if (containerRef.current?.clientWidth && chartRef.current) chartRef.current.applyOptions({ width: containerRef.current.clientWidth })
    }
    window.addEventListener('resize', onResize)
    return () => { window.removeEventListener('resize', onResize); chart.remove(); chartRef.current = null }
  }, [data])

  if (!data?.length) return null
  return (
    <div className="chart-card candle-chart-card" data-asset="vix">
      <h3>VIX (^VIX)</h3>
      <div ref={containerRef} className="candle-chart-container" />
    </div>
  )
}
