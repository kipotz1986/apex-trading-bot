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
import { TrendingUp, TrendingDown } from "lucide-react"

const positions = [
  {
    symbol: "BTC/USDT",
    side: "LONG",
    size: "$1,250.00",
    entry: "$64,200.00",
    current: "$64,520.40",
    pnl: "+$12.50 (+1.0%)",
    leverage: "5x",
    status: "profit"
  },
  {
    symbol: "ETH/USDT",
    side: "SHORT",
    size: "$800.00",
    entry: "$3,450.00",
    current: "$3,485.50",
    pnl: "-$8.20 (-0.8%)",
    leverage: "3x",
    status: "loss"
  },
  {
    symbol: "SOL/USDT",
    side: "LONG",
    size: "$500.00",
    entry: "$142.50",
    current: "$145.20",
    pnl: "+$9.45 (+1.9%)",
    leverage: "10x",
    status: "profit"
  }
]

export function PositionsTable() {
  return (
    <div className="w-full">
      <Table>
        <TableHeader className="bg-white/[0.02] border-y border-white/5">
          <TableRow className="border-none hover:bg-transparent">
            <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest pl-8">Symbol</TableHead>
            <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest text-center">Side</TableHead>
            <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest">Position Size</TableHead>
            <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest">Entry / Mark</TableHead>
            <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest">Unrealized PnL</TableHead>
            <TableHead className="text-[10px] font-bold text-white/30 uppercase tracking-widest text-right pr-8">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {positions.map((pos, i) => (
            <TableRow key={i} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors group">
              <TableCell className="py-5 pl-8">
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-white tracking-tight">{pos.symbol}</span>
                  <span className="text-[10px] text-white/20 font-medium">Bybit Perpetual</span>
                </div>
              </TableCell>
              
              <TableCell className="text-center">
                <Badge className={cn(
                  "px-2 py-0.5 rounded text-[9px] font-black tracking-widest",
                  pos.side === 'LONG' ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"
                )}>
                  {pos.side}
                </Badge>
              </TableCell>
              
              <TableCell>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white/80">{pos.size}</span>
                  <Badge variant="outline" className="text-[9px] text-white/30 border-white/5 px-1.5 h-4">
                    {pos.leverage}
                  </Badge>
                </div>
              </TableCell>
              
              <TableCell>
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-white/80 tracking-tighter">{pos.entry}</span>
                  <span className="text-[10px] text-white/30 font-medium tracking-tighter">{pos.current}</span>
                </div>
              </TableCell>
              
              <TableCell>
                <div className={cn(
                  "flex items-center gap-1.5 text-xs font-bold",
                  pos.status === 'profit' ? "text-emerald-500" : "text-red-500"
                )}>
                  {pos.status === 'profit' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                  {pos.pnl}
                </div>
              </TableCell>
              
              <TableCell className="text-right pr-8">
                 <button className="text-[10px] font-bold text-white/20 hover:text-red-400 transition-colors uppercase tracking-widest">
                   Close Position
                 </button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

// Need cn helper
import { cn } from "@/lib/utils"
