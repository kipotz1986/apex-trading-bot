"use client"

import React from "react"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts"
import { useEquityHistory } from "@/hooks/useApi"
import { useWebSocket } from "@/hooks/useWebSocket"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

// ─────────────────────────────────────────────────────────────────────────────
// Timeframe definitions
//
//  hours       – how far back the initial API fetch goes (0 = ALL)
//  updateSecs  – minimum seconds between appending a live WS point
//                0 means no live updates (rely on periodic refetch)
//  maxPoints   – cap on in-memory data points
//  tickGap     – minTickGap for the X-axis (avoids label crowding)
// ─────────────────────────────────────────────────────────────────────────────
const TIMEFRAMES = [
  { label: "1H",  hours: 1,   updateSecs: 5,   maxPoints: 120, tickGap: 20 },
  { label: "4H",  hours: 4,   updateSecs: 30,  maxPoints: 100, tickGap: 30 },
  { label: "1D",  hours: 24,  updateSecs: 60,  maxPoints: 100, tickGap: 40 },
  { label: "1W",  hours: 168, updateSecs: 0,   maxPoints: 200, tickGap: 60 },
  { label: "1M",  hours: 720, updateSecs: 0,   maxPoints: 500, tickGap: 80 },
  { label: "ALL", hours: 0,   updateSecs: 0,   maxPoints: 1000, tickGap: 80 },
] as const

type TFLabel = (typeof TIMEFRAMES)[number]["label"]

const userLocale = typeof navigator !== "undefined" ? navigator.language : undefined

function formatTick(iso: string, label: TFLabel): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  if (label === "1H") {
    return d.toLocaleTimeString(userLocale, { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" })
  }
  if (label === "4H" || label === "1D") {
    return d.toLocaleTimeString(userLocale, { hour12: false, hour: "2-digit", minute: "2-digit" })
  }
  // 1W → "Mon 14:30"
  if (label === "1W") {
    return d.toLocaleDateString(userLocale, { weekday: "short" }) + " " +
      d.toLocaleTimeString(userLocale, { hour12: false, hour: "2-digit", minute: "2-digit" })
  }
  // 1M / ALL → "May 11"
  return d.toLocaleDateString(userLocale, { month: "short", day: "numeric" })
}

export function EquityChart() {
  const [tfLabel, setTfLabel] = React.useState<TFLabel>("1D")
  const tf = TIMEFRAMES.find(t => t.label === tfLabel)!

  const { data: initialHistory, isLoading } = useEquityHistory(tf.hours)
  const [history, setHistory] = React.useState<{ time: string; equity: number }[]>([])

  // Timestamp (ms) of the last WS point we appended — used for throttling
  const lastWsAppendAt = React.useRef<number>(0)

  // Reset chart data whenever the timeframe changes or initial data arrives
  React.useEffect(() => {
    if (initialHistory) {
      setHistory(initialHistory)
    }
  }, [initialHistory])

  // Clear history instantly when user switches timeframe so the skeleton shows
  React.useEffect(() => {
    setHistory([])
    lastWsAppendAt.current = 0
  }, [tfLabel])

  // Live WebSocket updates — throttled per-timeframe
  useWebSocket("portfolio_update", (data: { equity: number; timestamp: string }) => {
    if (tf.updateSecs === 0) return // this timeframe doesn't use live appends

    const now = Date.now()
    if (now - lastWsAppendAt.current < tf.updateSecs * 1000) return

    lastWsAppendAt.current = now

    setHistory(prev => {
      const newPoint = { time: data.timestamp, equity: data.equity }
      return [...prev, newPoint].slice(-tf.maxPoints)
    })
  })

  if (isLoading && history.length === 0) {
    return <Skeleton className="h-[350px] w-full rounded-xl bg-muted/50" />
  }

  const chartData = history.map(item => ({
    ...item,
    formattedTime: formatTick(item.time, tfLabel),
  }))

  const isLive = tf.updateSecs > 0

  return (
    <div className="space-y-6">
      {/* Timeframe selectors */}
      <div className="flex justify-end gap-1 -mt-16 relative z-10">
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

      {/* Live indicator */}
      {isLive && (
        <div className="flex items-center gap-1.5 -mt-2 justify-end">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
          </span>
          <span className="text-[9px] font-bold text-primary/60 uppercase tracking-widest">
            Live · every {tf.updateSecs}s
          </span>
        </div>
      )}

      <div className="h-[350px] w-full">
        {chartData.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <p className="text-[10px] font-bold text-muted-foreground/60 uppercase tracking-widest">
              No data for this range
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
              <XAxis
                dataKey="formattedTime"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#ffffff20", fontSize: 10, fontWeight: 600 }}
                dy={10}
                minTickGap={tf.tickGap}
              />
              <YAxis
                domain={["auto", "auto"]}
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#ffffff20", fontSize: 10, fontWeight: 600 }}
                dx={-10}
                tickFormatter={val => `$${val.toLocaleString()}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#050B0A",
                  border: "1px solid #10b98130",
                  borderRadius: "12px",
                  fontSize: "11px",
                  fontWeight: "bold",
                  color: "#fff",
                }}
                itemStyle={{ color: "#10b981" }}
                cursor={{ stroke: "#10b98140", strokeWidth: 2 }}
                formatter={(value: any) => [`$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2 })}`, "Equity"]}
                labelFormatter={label => `Time: ${label}`}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stroke="#10b981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorEquity)"
                dot={false}
                isAnimationActive={!isLive}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
