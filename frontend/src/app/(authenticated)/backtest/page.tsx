"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { 
  Play, 
  History, 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Target,
  ChevronRight,
  Loader2,
  Calendar
} from "lucide-react"
import { useBacktest } from "@/hooks/useApi"
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from "recharts"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { format } from "date-fns"

export default function BacktestPage() {
  const [params, setParams] = useState({
    symbol: "BTC/USDT",
    timeframe: "1h",
    start_date: "2024-04-01",
    end_date: "2024-04-20",
    initial_balance: 10000
  })

  const { mutate: runBacktest, data, isPending } = useBacktest()

  const handleRun = () => {
    runBacktest({
        ...params,
        start_date: new Date(params.start_date).toISOString(),
        end_date: new Date(params.end_date).toISOString()
    }, {
        onError: (err: any) => {
            toast.error("Backtest Failed", {
                description: err.response?.data?.detail || "Make sure you have historical data in database."
            })
        }
    })
  }

  const chartData = data?.equity_curve?.map((item: any) => ({
    time: format(new Date(item.time), "MM/dd HH:mm"),
    value: item.value
  }))

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Strategy Backtester</h1>
          <p className="text-white/40 text-sm mt-1">Simulate multi-agent strategies against historical TimescaleDB data.</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        {/* Configuration Sidebar */}
        <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md h-fit">
          <CardHeader className="pb-4">
             <CardTitle className="text-[11px] font-bold uppercase tracking-widest text-white/40">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-bold text-white/30">Trading Pair</Label>
              <Input 
                value={params.symbol} 
                onChange={(e) => setParams({...params, symbol: e.target.value})}
                className="bg-white/5 border-white/5 h-10 text-xs font-bold"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-bold text-white/30">Start Date</Label>
              <Input 
                type="date"
                value={params.start_date} 
                onChange={(e) => setParams({...params, start_date: e.target.value})}
                className="bg-white/5 border-white/5 h-10 text-xs font-bold"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-bold text-white/30">End Date</Label>
              <Input 
                type="date"
                value={params.end_date} 
                onChange={(e) => setParams({...params, end_date: e.target.value})}
                className="bg-white/5 border-white/5 h-10 text-xs font-bold"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-[10px] uppercase font-bold text-white/30">Initial Capital ($)</Label>
              <Input 
                type="number"
                value={params.initial_balance} 
                onChange={(e) => setParams({...params, initial_balance: Number(e.target.value)})}
                className="bg-white/5 border-white/5 h-10 text-xs font-bold text-emerald-500"
              />
            </div>
            <Button 
              onClick={handleRun}
              disabled={isPending}
              className="w-full bg-emerald-500 hover:bg-emerald-400 text-black font-black uppercase tracking-widest text-[10px] py-6 shadow-[0_0_20px_rgba(16,185,129,0.2)] group"
            >
              {isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2 fill-black group-hover:scale-110 transition-transform" /> 
                  Run Simulation
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Results Area */}
        <div className="lg:col-span-3 space-y-6">
          {!data && !isPending && (
             <div className="h-[500px] rounded-3xl border-2 border-dashed border-white/5 flex flex-col items-center justify-center text-white/10 space-y-4">
                <History className="w-16 h-16 opacity-20" />
                <p className="font-bold uppercase tracking-[0.3em] text-[10px]">Awaiting Simulation Parameters</p>
             </div>
          )}

          {isPending && (
            <div className="h-[500px] rounded-3xl bg-white/[0.02] border border-white/5 flex flex-col items-center justify-center space-y-6">
               <div className="relative">
                  <div className="w-20 h-20 rounded-full border-2 border-emerald-500/20 border-t-emerald-500 animate-spin" />
                  <Activity className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 text-emerald-500 animate-pulse" />
               </div>
               <div className="text-center">
                  <p className="text-white font-bold tracking-widest uppercase text-xs">Simulating Neural Network Decisions</p>
                  <p className="text-white/20 text-[10px] mt-2 italic font-medium">Crunching historical candlestick data...</p>
               </div>
            </div>
          )}

          {data && (
            <>
              {/* Stats Cards */}
              <div className="grid gap-4 md:grid-cols-4">
                 {[
                   { label: "Final Balance", val: `$${data.final_balance.toLocaleString()}`, icon: TrendingUp, color: "emerald" },
                   { label: "Net Return", val: `${data.total_return_pct}%`, icon: Activity, color: "blue" },
                   { label: "Win Rate", val: `${data.win_rate}%`, icon: Target, color: "emerald" },
                   { label: "Sharpe Ratio", val: data.sharpe_ratio, icon: Activity, color: "amber" },
                 ].map(stat => (
                   <Card key={stat.label} className="bg-white/5 border-white/5">
                      <CardContent className="p-4 flex items-center justify-between">
                         <div>
                            <p className="text-[9px] font-bold text-white/30 uppercase tracking-widest mb-1">{stat.label}</p>
                            <p className={cn("text-xl font-bold tracking-tight", stat.color === 'emerald' ? 'text-emerald-500' : 'text-white')}>{stat.val}</p>
                         </div>
                         <stat.icon className={`w-5 h-5 text-${stat.color}-500/50`} />
                      </CardContent>
                   </Card>
                 ))}
              </div>

              {/* Chart */}
              <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
                 <CardHeader>
                    <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-white/40">Equity Growth Path</CardTitle>
                 </CardHeader>
                 <CardContent>
                    <div className="h-[300px] w-full">
                       <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={chartData}>
                             <defs>
                                <linearGradient id="backtestGradient" x1="0" y1="0" x2="0" y2="1">
                                   <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                                   <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                                </linearGradient>
                             </defs>
                             <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                             <XAxis 
                               dataKey="time" 
                               axisLine={false} 
                               tickLine={false} 
                               tick={{ fill: '#ffffff20', fontSize: 9 }}
                             />
                             <YAxis 
                               domain={['auto', 'auto']} 
                               axisLine={false} 
                               tickLine={false} 
                               tick={{ fill: '#ffffff20', fontSize: 9 }}
                               tickFormatter={(val) => `$${val}`}
                             />
                             <Tooltip 
                                contentStyle={{ backgroundColor: '#050B0A', border: '1px solid #ffffff10', borderRadius: '12px' }}
                             />
                             <Area 
                                type="monotone" 
                                dataKey="value" 
                                stroke="#10b981" 
                                strokeWidth={2}
                                fill="url(#backtestGradient)" 
                             />
                          </AreaChart>
                       </ResponsiveContainer>
                    </div>
                 </CardContent>
              </Card>

              {/* Trade Log */}
              <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md overflow-hidden">
                 <CardHeader className="border-b border-white/5 py-4">
                    <CardTitle className="text-[10px] font-bold uppercase tracking-widest text-white/40">Execution Log ({data.trades?.length || 0} Trades)</CardTitle>
                 </CardHeader>
                 <CardContent className="p-0 max-h-[300px] overflow-y-auto">
                    <div className="divide-y divide-white/5">
                       {data.trades?.map((trade: any, i: number) => (
                          <div key={i} className="px-6 py-4 flex items-center justify-between hover:bg-white/[0.02] transition-all">
                             <div className="flex items-center gap-4">
                                <div className={cn(
                                   "p-1.5 rounded-md",
                                   trade.pnl > 0 ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"
                                )}>
                                   {trade.side === 'LONG' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                </div>
                                <div className="space-y-0.5">
                                   <p className="text-xs font-bold text-white">{trade.side} @ ${trade.entry_price.toLocaleString()}</p>
                                   <p className="text-[9px] text-white/30 font-medium">Exit: {format(new Date(trade.exit_time), "yyyy-MM-dd HH:mm")}</p>
                                </div>
                             </div>
                             <div className="text-right">
                                <p className={cn("text-xs font-bold", trade.pnl > 0 ? "text-emerald-500" : "text-red-500")}>
                                   {trade.pnl > 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                                </p>
                                <p className="text-[9px] font-bold text-white/10 tracking-widest uppercase">PNL USD</p>
                             </div>
                          </div>
                       ))}
                    </div>
                 </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
