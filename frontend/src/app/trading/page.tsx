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
import { Calendar, Search, Download, ChevronLeft, ChevronRight } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

const tradeHistory = [
  {
    pair: "BTC/USDT",
    side: "LONG",
    pnl: "+$420.50",
    status: "PROFIT",
    entry: "$62,400.00",
    exit: "$63,850.00",
    date: "2024-04-20 14:30",
    reason: "RSI Oversold + Whale Accumulation"
  },
  {
    pair: "ETH/USDT",
    side: "SHORT",
    pnl: "-$125.20",
    status: "LOSS",
    entry: "$3,520.00",
    exit: "$3,545.00",
    date: "2024-04-20 10:15",
    reason: "Stop Loss Triggered (MA Crossdown)"
  },
  {
    pair: "SOL/USDT",
    side: "LONG",
    pnl: "+$85.00",
    status: "PROFIT",
    entry: "$138.20",
    exit: "$141.50",
    date: "2024-04-19 22:45",
    reason: "Breakout Confirmation v3"
  }
]

export default function TradingHistoryPage() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Trade History</h1>
          <p className="text-white/40 text-sm mt-1">Audit log of all executed trades and AI reasoning.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="bg-white/5 border-white/5 hover:bg-white/10 text-xs gap-2">
            <Download className="w-4 h-4" /> Export CSV
          </Button>
        </div>
      </div>

      <div className="flex gap-4 items-center">
        <div className="relative group flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30 group-focus-within:text-emerald-500 transition-colors" />
          <Input 
            className="bg-white/5 border-white/5 pl-10 h-10 text-xs font-semibold" 
            placeholder="Search by pair or reason..."
          />
        </div>
        <Button variant="outline" className="bg-white/5 border-white/5 text-xs gap-2 h-10">
           <Calendar className="w-4 h-4" /> All Time
        </Button>
      </div>

      <div className="rounded-2xl border border-white/5 bg-[#050B0A]/50 backdrop-blur-md overflow-hidden">
        <Table>
          <TableHeader className="bg-white/[0.02]">
            <TableRow className="hover:bg-transparent border-white/5">
              <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest pl-8">Pair / Date</TableHead>
              <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest">Side</TableHead>
              <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest">Execution Price</TableHead>
              <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest">Result</TableHead>
              <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest">AI Reasoning Summary</TableHead>
              <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest text-right pr-8">Details</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tradeHistory.map((trade, i) => (
              <TableRow key={i} className="group border-white/5 hover:bg-white/[0.03] transition-colors">
                <TableCell className="pl-8 py-5">
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-white">{trade.pair}</span>
                    <span className="text-[10px] text-white/20 font-medium">{trade.date}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className={cn(
                    "text-[9px] font-black tracking-widest",
                    trade.side === 'LONG' ? "text-emerald-500 border-emerald-500/20 bg-emerald-500/5" : "text-red-500 border-red-500/20 bg-red-500/5"
                  )}>
                    {trade.side}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-white/80">{trade.exit}</span>
                    <span className="text-[10px] text-white/20 line-through">from {trade.entry}</span>
                  </div>
                </TableCell>
                <TableCell>
                   <div className={cn(
                     "text-xs font-bold",
                     trade.status === 'PROFIT' ? "text-emerald-500" : "text-red-500"
                   )}>
                     {trade.pnl}
                   </div>
                </TableCell>
                <TableCell className="max-w-[200px]">
                   <p className="text-[11px] text-white/50 leading-relaxed truncate group-hover:text-white/80 transition-colors italic">
                     "{trade.reason}"
                   </p>
                </TableCell>
                <TableCell className="text-right pr-8">
                   <Button variant="ghost" size="sm" className="text-[10px] font-bold text-emerald-500/50 hover:text-emerald-400 hover:bg-emerald-500/5 uppercase tracking-widest">
                     View Log
                   </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        <div className="px-8 py-4 bg-white/[0.01] border-t border-white/5 flex items-center justify-between">
           <p className="text-[10px] font-bold text-white/20 uppercase">Showing 1-10 of 1,240 trades</p>
           <div className="flex gap-2">
              <Button disabled variant="outline" size="icon" className="w-8 h-8 bg-white/5 border-white/5 text-white/20">
                 <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="icon" className="w-8 h-8 bg-white/5 border-white/5 text-white/40 hover:text-white">
                 <ChevronRight className="w-4 h-4" />
              </Button>
           </div>
        </div>
      </div>
    </div>
  )
}

// Helper cn from positions component
import { cn } from "@/lib/utils"
