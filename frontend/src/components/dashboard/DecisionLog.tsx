"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Clock, Brain, MessageSquare, ChevronRight } from "lucide-react"

import { useAgentDecisions } from "@/hooks/useApi"
import { AgentDecision } from "@/types/api"
import { format } from "date-fns"
import { cn } from "@/lib/utils"

export function DecisionLog() {
  const { data: decisions = [], isLoading } = useAgentDecisions(10)
  return (
    <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between border-b border-white/5 pb-4 px-6 pt-5">
        <div className="flex items-center gap-2">
           <Brain className="w-4 h-4 text-emerald-500" />
           <CardTitle className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/40">
             AI Decision Engine
           </CardTitle>
        </div>
        <button className="text-[9px] font-black text-emerald-500/50 hover:text-emerald-500 transition-colors uppercase tracking-widest">
           View Matrix
        </button>
      </CardHeader>
      
      <CardContent className="p-0">
        <div className="divide-y divide-white/5">
          {isLoading ? (
            <div className="p-10 text-center text-[10px] font-bold text-white/20 uppercase tracking-widest">
              Loading decisions...
            </div>
          ) : decisions.length === 0 ? (
            <div className="p-10 text-center text-[10px] font-bold text-white/20 uppercase tracking-widest">
              No decisions logged
            </div>
          ) : (
            decisions.map((dec: AgentDecision) => (
              <div key={dec.id} className="p-5 hover:bg-white/[0.02] transition-all cursor-pointer group relative">
                 <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                       <span className="text-[10px] font-mono text-emerald-500/50">
                         {format(new Date(dec.timestamp), "HH:mm:ss")}
                       </span>
                       <Badge variant="outline" className="text-[9px] font-black border-white/10 group-hover:border-emerald-500/30 transition-colors">
                          {dec.symbol}
                       </Badge>
                       <span className={cn(
                         "text-[10px] font-black uppercase tracking-tighter",
                         dec.action.includes('BUY') || dec.action.includes('LONG') ? "text-emerald-500" : dec.action.includes('SELL') || dec.action.includes('SHORT') ? "text-red-500" : "text-amber-500"
                       )}>
                          {dec.action}
                       </span>
                    </div>
                    <div className="flex items-center gap-2">
                       <span className="text-[9px] font-bold text-white/20 uppercase">Consensus</span>
                       <span className="text-xs font-bold text-white">{Math.round(dec.consensus_score * 100)}%</span>
                    </div>
                 </div>
  
                 <p className="text-[11px] text-white/50 leading-relaxed font-medium mb-4 line-clamp-2 italic">
                   "{dec.reasoning}"
                 </p>
  
                 <div className="flex items-center justify-between">
                    <div className="flex gap-2">
                       {/* Transform agent_signals map to displayable items */}
                       {Object.entries(dec.agent_signals || {}).map(([name, signal]: [string, any], i) => (
                         <div key={i} className="flex flex-col items-center">
                            <span className="text-[7px] font-black text-white/20 mb-1">{name.toUpperCase().substring(0, 3)}</span>
                            <div className={cn(
                              "w-5 h-5 rounded-md flex items-center justify-center text-[9px] font-black",
                              signal === 'BUY' ? "bg-emerald-500/10 text-emerald-500" : signal === 'SELL' ? "bg-red-500/10 text-red-500" : "bg-white/5 text-white/40"
                            )}>
                              {signal === 'BUY' ? 'B' : signal === 'SELL' ? 'S' : 'H'}
                            </div>
                         </div>
                       ))}
                    </div>
                    <ChevronRight className="w-4 h-4 text-white/10 group-hover:text-emerald-500 group-hover:translate-x-1 transition-all" />
                 </div>
              </div>
            ))
          )}
        </div>
        
        <button className="w-full py-4 bg-white/[0.01] hover:bg-white/[0.03] text-[9px] font-bold text-white/20 hover:text-white transition-all uppercase tracking-[0.2em] border-t border-white/5">
           Deep Analysis Log →
        </button>
      </CardContent>
    </Card>
  )
}
