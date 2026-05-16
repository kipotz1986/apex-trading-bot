"use client"

import React from "react"
import { createChart, CandlestickSeries, TickMarkType } from "lightweight-charts"
import { useWebSocket } from "@/hooks/useWebSocket"
import { useTradingSymbols } from "@/hooks/useApi"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"

// Resolved once — uses client's navigator.language automatically
const userLocale = typeof navigator !== "undefined" ? navigator.language : undefined

function fmtTime(unixSec: number, opts: Intl.DateTimeFormatOptions) {
  return new Date(unixSec * 1000).toLocaleString(userLocale, opts)
}

// Convert API symbol "BTC/USDT:USDT" → display "BTC/USDT"
const toDisplaySymbol = (apiSymbol: string) => apiSymbol.replace(":USDT", "")

const TIMEFRAMES = [
  { label: "1m",  bybitInterval: "1",   ccxt: "1m"  },
  { label: "5m",  bybitInterval: "5",   ccxt: "5m"  },
  { label: "15m", bybitInterval: "15",  ccxt: "15m" },
  { label: "1H",  bybitInterval: "60",  ccxt: "1h"  },
  { label: "4H",  bybitInterval: "240", ccxt: "4h"  },
] as const
type TFLabel = (typeof TIMEFRAMES)[number]["label"]

export function CandlestickChart() {
  const containerRef = React.useRef<HTMLDivElement>(null)
  const chartRef = React.useRef<ReturnType<typeof createChart> | null>(null)
  const seriesRef = React.useRef<any>(null)

  // Symbols come from active trading config — falls back to BTC if not loaded
  const { data: symbolData } = useTradingSymbols()
  const SYMBOLS = React.useMemo(() => {
    if (!symbolData) return ["BTC/USDT"]
    return symbolData.active.map(toDisplaySymbol)
  }, [symbolData])

  const [symbol, setSymbol] = React.useState<string>("BTC/USDT")
  const [tfLabel, setTfLabel] = React.useState<TFLabel>("15m")
  const [isLoading, setIsLoading] = React.useState(false)

  // Auto-pick first available symbol when list loads / changes
  React.useEffect(() => {
    if (SYMBOLS.length > 0 && !SYMBOLS.includes(symbol)) {
      setSymbol(SYMBOLS[0])
    }
  }, [SYMBOLS, symbol])

  const tf = TIMEFRAMES.find(t => t.label === tfLabel)!

  // ── Create chart once ──────────────────────────────────────────────────────
  React.useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "transparent" },
        textColor: "rgba(255,255,255,0.3)",
        fontFamily: "'Inter', sans-serif",
        fontSize: 10,
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      crosshair: {
        vertLine: { color: "rgba(16,185,129,0.4)", labelBackgroundColor: "#10b981" },
        horzLine: { color: "rgba(16,185,129,0.4)", labelBackgroundColor: "#10b981" },
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.06)",
        textColor: "rgba(255,255,255,0.3)",
      },
      // Crosshair tooltip time label — shows full local date+time
      localization: {
        locale: userLocale,
        timeFormatter: (unixSec: number) =>
          fmtTime(unixSec, {
            month: "short", day: "numeric",
            hour: "2-digit", minute: "2-digit", hour12: false,
          }),
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.06)",
        timeVisible: true,
        secondsVisible: false,
        // Tick labels on the time axis — client local timezone
        tickMarkFormatter: (unixSec: number, type: TickMarkType) => {
          if (type === TickMarkType.Year)
            return fmtTime(unixSec, { year: "numeric" })
          if (type === TickMarkType.Month)
            return fmtTime(unixSec, { month: "short" })
          if (type === TickMarkType.DayOfMonth)
            return fmtTime(unixSec, { month: "short", day: "numeric" })
          // Time / TimeWithSeconds
          return fmtTime(unixSec, { hour: "2-digit", minute: "2-digit", hour12: false })
        },
      },
      handleScroll: true,
      handleScale: true,
    })

    const series = chart.addSeries(CandlestickSeries, {
      upColor:          "#10b981",
      downColor:        "#ef4444",
      borderUpColor:    "#10b981",
      borderDownColor:  "#ef4444",
      wickUpColor:      "#10b981",
      wickDownColor:    "#ef4444",
    })

    chartRef.current = chart
    seriesRef.current = series

    const observer = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({
          width:  containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        })
      }
    })
    observer.observe(containerRef.current)

    return () => {
      observer.disconnect()
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [])

  // ── Load initial candles on symbol / timeframe change ─────────────────────
  React.useEffect(() => {
    if (!seriesRef.current) return
    setIsLoading(true)
    api.get("/portfolio/klines", { params: { symbol, timeframe: tf.ccxt, limit: 200 } })
      .then(({ data }) => {
        if (seriesRef.current && data.length) {
          seriesRef.current.setData(data)
          chartRef.current?.timeScale().fitContent()
        }
      })
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [symbol, tfLabel])

  // ── Live WS candle updates ─────────────────────────────────────────────────
  useWebSocket("kline", (data: {
    symbol: string
    timeframe: string
    candle: { time: number; open: number; high: number; low: number; close: number; volume: number; confirmed: boolean }
  }) => {
    if (data.symbol !== symbol) return
    if (data.timeframe !== tf.bybitInterval) return
    if (!seriesRef.current) return
    seriesRef.current.update(data.candle)
  })

  return (
    <div className="space-y-4">
      {/* Controls row */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        {/* Symbol selector */}
        <div className="flex gap-1">
          {SYMBOLS.map(s => (
            <button
              key={s}
              onClick={() => setSymbol(s)}
              className={cn(
                "px-3 py-1.5 rounded-md text-[10px] font-bold transition-all",
                symbol === s
                  ? "bg-primary/10 text-primary border border-primary/20"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Timeframe selector */}
        <div className="flex gap-1">
          {TIMEFRAMES.map(t => (
            <button
              key={t.label}
              onClick={() => setTfLabel(t.label)}
              className={cn(
                "px-3 py-1 rounded-md text-[10px] font-bold transition-all",
                tfLabel === t.label
                  ? "bg-primary/10 text-primary border border-primary/20"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Live dot */}
      <div className="flex items-center gap-1.5 -mt-1 justify-end">
        <span className="relative flex h-1.5 w-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
        </span>
        <span className="text-[9px] font-bold text-primary/60 uppercase tracking-widest">Live</span>
      </div>

      {/* Chart container */}
      <div className="relative h-[380px] w-full">
        {isLoading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-popover/60 rounded-xl">
            <span className="text-[10px] font-bold text-muted-foreground/80 uppercase tracking-widest animate-pulse">Loading…</span>
          </div>
        )}
        <div ref={containerRef} className="h-full w-full" />
      </div>
    </div>
  )
}
