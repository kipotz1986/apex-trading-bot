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
import { TrendingUp, TrendingDown, Loader2 } from "lucide-react"
import { useOpenPositions } from "@/hooks/useApi"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

export function PositionsTable() {
  const { data: positions, isLoading } = useOpenPositions();

  if (isLoading) {
    return (
      <div className="p-8 space-y-4">
        {[1, 2, 3].map(i => (
          <Skeleton key={i} className="h-12 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (!positions || positions.length === 0) {
    return (
      <div className="p-12 text-center space-y-2">
        <p className="text-sm font-bold text-white/40 uppercase tracking-widest">No Active Positions</p>
        <p className="text-[10px] text-white/20 font-medium">Bot is currently scanning for entry signals.</p>
      </div>
    );
  }

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
          {positions.map((pos) => (
            <TableRow key={pos.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors group">
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
                  <span className="text-xs font-bold text-white/80">${pos.size.toLocaleString()}</span>
                  <Badge variant="outline" className="text-[9px] text-white/30 border-white/5 px-1.5 h-4">
                    {pos.leverage}x
                  </Badge>
                </div>
              </TableCell>
              
              <TableCell>
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-white/80 tracking-tighter">${pos.entry.toLocaleString()}</span>
                  <span className="text-[10px] text-white/30 font-medium tracking-tighter">${pos.current.toLocaleString()}</span>
                </div>
              </TableCell>
              
              <TableCell>
                <div className={cn(
                  "flex items-center gap-1.5 text-xs font-bold",
                  pos.status === 'profit' ? "text-emerald-500" : "text-red-500"
                )}>
                  {pos.status === 'profit' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                  {pos.pnl >= 0 ? '+' : ''}{pos.pnl.toFixed(2)} ({pos.pnl_percent.toFixed(2)}%)
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
