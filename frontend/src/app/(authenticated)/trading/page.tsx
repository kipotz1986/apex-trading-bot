"use client"

import React from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Calendar, Search, Download, ChevronLeft, ChevronRight, TrendingUp, TrendingDown, DollarSign, BarChart2, Target } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

import { useTradeHistory, useTradeStats, useTradeDetail } from "@/hooks/useApi"
import { api } from "@/lib/api"
import { Trade } from "@/types/api"
import { cn } from "@/lib/utils"
import { fmtDateTime, fmtDateTimeSec, fmtDateShort, fmtDateISO } from "@/lib/dateFormat"

function TradeDetailModal({ tradeId, onClose }: { tradeId: number | null, onClose: () => void }) {
  const { data: trade, isLoading } = useTradeDetail(tradeId)

  return (
    <Dialog open={tradeId !== null} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="bg-[#0A0F0E] border-white/10 text-white max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-sm font-bold tracking-tight text-white uppercase">
            Trade Log #{tradeId}
          </DialogTitle>
        </DialogHeader>
        {isLoading ? (
          <div className="py-8 text-center text-white/30 text-xs font-bold uppercase tracking-widest">Loading...</div>
        ) : trade ? (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Symbol", value: trade.symbol },
                { label: "Side", value: trade.side },
                { label: "Status", value: trade.status },
                { label: "Entry Price", value: trade.entry_price ? `$${trade.entry_price.toLocaleString()}` : "—" },
                { label: "Exit Price", value: trade.exit_price ? `$${trade.exit_price.toLocaleString()}` : "—" },
                { label: "PnL", value: trade.pnl_usd != null ? `${trade.pnl_usd >= 0 ? '+' : ''}$${trade.pnl_usd.toFixed(2)}` : "—" },
              ].map(({ label, value }) => (
                <div key={label} className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
                  <p className="text-[9px] font-bold text-white/30 uppercase tracking-widest mb-1">{label}</p>
                  <p className="text-xs font-bold text-white">{value}</p>
                </div>
              ))}
            </div>
            {trade.meta_data?.reasoning && (
              <div className="p-4 rounded-xl bg-emerald-500/[0.03] border border-emerald-500/10">
                <p className="text-[9px] font-bold text-emerald-500/50 uppercase tracking-widest mb-2">AI Reasoning</p>
                <p className="text-xs text-white/60 leading-relaxed italic">"{trade.meta_data.reasoning}"</p>
              </div>
            )}
            {trade.meta_data && Object.keys(trade.meta_data).filter(k => k !== 'reasoning' && k !== 'exit_price').length > 0 && (
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                <p className="text-[9px] font-bold text-white/30 uppercase tracking-widest mb-2">Metadata</p>
                <pre className="text-[10px] font-mono text-white/50 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(Object.fromEntries(Object.entries(trade.meta_data).filter(([k]) => k !== 'reasoning')), null, 2)}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <div className="py-8 text-center text-white/30 text-xs font-bold uppercase tracking-widest">Trade not found</div>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default function TradingHistoryPage() {
  const [page, setPage] = React.useState(1)
  const [search, setSearch] = React.useState("")
  const [sideFilter, setSideFilter] = React.useState<string>("ALL")
  const [selectedTradeId, setSelectedTradeId] = React.useState<number | null>(null)
  const [isExporting, setIsExporting] = React.useState(false)

  const handleExportCSV = async () => {
    setIsExporting(true)
    try {
      const { data: result } = await api.get("/trades/", { params: { page: 1, per_page: 1000 } })
      const trades: Trade[] = result.trades || []
      const headers = ["ID", "Symbol", "Side", "Entry Price", "Exit Price", "PnL (USD)", "Date", "Status", "Reasoning"]
      const rows = trades.map(t => [
        t.id,
        t.symbol,
        t.side,
        t.entry_price ?? "",
        t.exit_price ?? "",
        t.pnl_usd ?? "",
        fmtDateTimeSec(t.created_at),
        t.status,
        `"${(t.meta_data?.reasoning || "").replace(/"/g, '""')}"`
      ])
      const csv = [headers.join(","), ...rows.map(r => r.join(","))].join("\n")
      const blob = new Blob([csv], { type: "text/csv" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `trades_${fmtDateISO()}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setIsExporting(false)
    }
  }

  const { data, isLoading } = useTradeHistory(page, 10)
  const { data: chartData } = useTradeHistory(1, 100)
  const { data: stats } = useTradeStats()

  const allTrades = data?.trades || []
  const total = data?.total || 0

  // Client-side search/filter
  const trades = allTrades.filter(t => {
    const matchSearch = !search ||
      t.symbol.toLowerCase().includes(search.toLowerCase()) ||
      (t.meta_data?.reasoning || "").toLowerCase().includes(search.toLowerCase())
    const matchSide = sideFilter === "ALL" || t.side === sideFilter
    return matchSearch && matchSide
  })

  // Cumulative P&L chart from most recent 100 trades (ascending order)
  const cumulativeData = React.useMemo(() => {
    if (!chartData?.trades) return []
    const sorted = [...chartData.trades].reverse()
    let cumPnl = 0
    return sorted.map(t => {
      cumPnl += t.pnl_usd || 0
      return {
        date: fmtDateShort(t.created_at),
        cumPnl: parseFloat(cumPnl.toFixed(2))
      }
    })
  }, [chartData])

  const statCards = [
    { label: "Total Trades", value: stats?.total_trades?.toLocaleString() ?? "—", icon: BarChart2, color: "blue" },
    { label: "Win Rate", value: stats?.win_rate != null ? `${stats.win_rate}%` : "—", icon: Target, color: "emerald" },
    { label: "Total PnL", value: stats?.total_pnl != null ? `${stats.total_pnl >= 0 ? '+' : ''}$${stats.total_pnl.toFixed(2)}` : "—", icon: DollarSign, color: (stats?.total_pnl ?? 0) >= 0 ? "emerald" : "red" },
    { label: "Profit Factor", value: stats?.profit_factor != null ? stats.profit_factor.toFixed(2) : (stats?.total_trades ?? 0) > 0 ? "∞" : "—", icon: TrendingUp, color: "amber" },
  ]

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Trade History</h1>
          <p className="text-white/40 text-sm mt-1">Audit log of all executed trades and AI reasoning.</p>
        </div>
        <Button
          variant="outline"
          className="bg-white/5 border-white/5 hover:bg-white/10 text-xs gap-2"
          onClick={handleExportCSV}
          disabled={isExporting}
        >
          <Download className="w-4 h-4" /> {isExporting ? "Exporting..." : "Export CSV"}
        </Button>
      </div>

      {/* Stats Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((s) => (
          <Card key={s.label} className="bg-white/5 border-white/5 backdrop-blur-sm">
            <CardContent className="p-5 flex items-center gap-4">
              <div className={`p-2.5 rounded-xl bg-${s.color}-500/10 border border-${s.color}-500/20`}>
                <s.icon className={`w-4 h-4 text-${s.color}-500`} />
              </div>
              <div>
                <p className="text-[10px] font-bold text-white/30 uppercase tracking-widest">{s.label}</p>
                <p className="text-lg font-bold text-white tracking-tight">{s.value}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Cumulative P&L Chart */}
      {cumulativeData.length > 1 && (
        <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/40">
              Cumulative P&amp;L
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={cumulativeData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                  <XAxis
                    dataKey="date"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#ffffff20', fontSize: 10, fontWeight: 600 }}
                    dy={8}
                    minTickGap={40}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#ffffff20', fontSize: 10, fontWeight: 600 }}
                    dx={-8}
                    tickFormatter={(v) => `$${v}`}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#050B0A', border: '1px solid #10b98130', borderRadius: '10px', fontSize: '11px', fontWeight: 'bold', color: '#fff' }}
                    itemStyle={{ color: '#10b981' }}
                    formatter={(value: any) => [`$${value.toLocaleString()}`, "Cum. PnL"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="cumPnl"
                    stroke="#10b981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorPnl)"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <div className="relative group flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30 group-focus-within:text-emerald-500 transition-colors" />
          <Input
            className="bg-white/5 border-white/5 pl-10 h-10 text-xs font-semibold"
            placeholder="Search by pair or reasoning..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          />
        </div>
        <Select value={sideFilter} onValueChange={(v) => { setSideFilter(v ?? "ALL"); setPage(1) }}>
          <SelectTrigger className="w-[120px] bg-white/5 border-white/5 text-[10px] font-bold uppercase tracking-widest h-10">
            <SelectValue placeholder="Side" />
          </SelectTrigger>
          <SelectContent className="bg-[#050B0A] border-white/10 text-white">
            <SelectItem value="ALL">All Sides</SelectItem>
            <SelectItem value="BUY">BUY</SelectItem>
            <SelectItem value="SELL">SELL</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="rounded-2xl border border-white/5 bg-[#050B0A]/50 backdrop-blur-md overflow-hidden">
        <Table>
          <TableHeader className="bg-white/[0.02]">
            <TableRow className="hover:bg-transparent border-white/5">
              <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest pl-8">Pair / Date</TableHead>
              <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest">Side</TableHead>
              <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest">Entry / Exit</TableHead>
              <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest">Result</TableHead>
              <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest">AI Reasoning</TableHead>
              <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest text-right pr-8">Details</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-20 text-white/20 font-bold uppercase tracking-widest">
                  Loading trades...
                </TableCell>
              </TableRow>
            ) : trades.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-20 text-white/20 font-bold uppercase tracking-widest">
                  No trades found
                </TableCell>
              </TableRow>
            ) : (
              trades.map((trade: Trade) => (
                <TableRow key={trade.id} className="group border-white/5 hover:bg-white/[0.03] transition-colors">
                  <TableCell className="pl-8 py-5">
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-white">{trade.symbol}</span>
                      <span className="text-[10px] text-white/20 font-medium">
                        {fmtDateTime(trade.created_at)}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={cn(
                      "text-[9px] font-black tracking-widest",
                      trade.side === 'BUY' ? "text-emerald-500 border-emerald-500/20 bg-emerald-500/5" : "text-red-500 border-red-500/20 bg-red-500/5"
                    )}>
                      {trade.side}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-white/80">
                        Entry: ${trade.entry_price?.toLocaleString() || '—'}
                      </span>
                      <span className="text-[10px] text-white/40 font-medium">
                        Exit: ${trade.exit_price?.toLocaleString() || '—'}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className={cn(
                      "text-xs font-bold",
                      (trade.pnl_usd || 0) > 0 ? "text-emerald-500" : "text-red-500"
                    )}>
                      {(trade.pnl_usd || 0) > 0 ? "+" : ""}${trade.pnl_usd?.toFixed(2) || '0.00'}
                    </div>
                  </TableCell>
                  <TableCell className="max-w-[200px]">
                    <p className="text-[11px] text-white/50 leading-relaxed truncate group-hover:text-white/80 transition-colors italic">
                      "{trade.meta_data?.reasoning || "Automatic execution"}"
                    </p>
                  </TableCell>
                  <TableCell className="text-right pr-8">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedTradeId(trade.id)}
                      className="text-[10px] font-bold text-emerald-500/50 hover:text-emerald-400 hover:bg-emerald-500/5 uppercase tracking-widest"
                    >
                      View Log
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        <div className="px-8 py-4 bg-white/[0.01] border-t border-white/5 flex items-center justify-between">
          <p className="text-[10px] font-bold text-white/20 uppercase">
            {total > 0 ? `Showing ${(page - 1) * 10 + 1}–${Math.min(page * 10, total)} of ${total.toLocaleString()} trades` : "No trades"}
          </p>
          <div className="flex gap-2">
            <Button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              variant="outline" size="icon" className="w-8 h-8 bg-white/5 border-white/5 text-white/40"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button
              onClick={() => setPage(p => p + 1)}
              disabled={page * 10 >= total}
              variant="outline" size="icon" className="w-8 h-8 bg-white/5 border-white/5 text-white/40 hover:text-white"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      <TradeDetailModal tradeId={selectedTradeId} onClose={() => setSelectedTradeId(null)} />
    </div>
  )
}
