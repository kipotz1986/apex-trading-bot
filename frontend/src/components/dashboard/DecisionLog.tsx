"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Clock, Brain, MessageSquare, ChevronRight } from "lucide-react"

import { useAgentDecisions } from "@/hooks/useApi"
import { AgentDecision } from "@/types/api"
import { cn } from "@/lib/utils"
import { fmtDateTime } from "@/lib/dateFormat"

export function DecisionLog() {
  const { data: decisions = [], isLoading } = useAgentDecisions(10)
  return (
    <Card className="glass-card backdrop-blur-md overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/50 pb-4 px-6 pt-5">
        <div className="flex items-center gap-2">
           <Brain className="w-4 h-4 text-primary" />
           <CardTitle className="text-[11px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
             AI Decision Engine
           </CardTitle>
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        <div className="divide-y divide-border/50">
          {isLoading ? (
            <div className="p-10 text-center text-[10px] font-bold text-muted-foreground/60 uppercase tracking-widest">
              Loading decisions...
            </div>
          ) : decisions.length === 0 ? (
            <div className="p-10 text-center text-[10px] font-bold text-muted-foreground/60 uppercase tracking-widest">
              No decisions logged
            </div>
          ) : (
            decisions.map((dec: AgentDecision) => (
              <div key={dec.id} className="p-5 hover:bg-muted/20 transition-all cursor-pointer group relative">
                 <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                       <span className="text-[10px] font-mono text-primary/50">
                         {fmtDateTime(dec.timestamp)}
                       </span>
                       <Badge variant="outline" className="text-[9px] font-black border-border group-hover:border-emerald-500/30 transition-colors">
                          {dec.symbol}
                       </Badge>
                       <span className={cn(
                         "text-[10px] font-black uppercase tracking-tighter",
                         dec.action.includes('BUY') || dec.action.includes('LONG') ? "text-primary" : dec.action.includes('SELL') || dec.action.includes('SHORT') ? "text-red-500" : "text-amber-500"
                       )}>
                          {dec.action}
                       </span>
                    </div>
                    <div className="flex items-center gap-2">
                       <span className="text-[9px] font-bold text-muted-foreground/60 uppercase">Consensus</span>
                       <span className="text-xs font-bold text-foreground">{Math.round(dec.consensus_score * 100)}%</span>
                    </div>
                 </div>
  
                 <p className="text-[11px] text-muted-foreground leading-relaxed font-medium mb-4 line-clamp-2 italic">
                   "{dec.reasoning}"
                 </p>
  
                 <div className="flex items-center justify-between">
                     <div className="flex gap-2">
                        {/* Transform agent_signals map to displayable items */}
                        {Object.entries(dec.agent_signals || {}).map(([name, signalObj]: [string, any], i) => {
                           const sigVal = typeof signalObj === 'string' ? signalObj : (signalObj?.signal || 'HOLD');
                           const isBuy = sigVal.includes('BUY') || sigVal.includes('LONG');
                           const isSell = sigVal.includes('SELL') || sigVal.includes('SHORT');
                           
                           return (
                             <div key={i} className="flex flex-col items-center">
                                <span className="text-[7px] font-black text-muted-foreground/60 mb-1">{name.toUpperCase().substring(0, 3)}</span>
                                <div className={cn(
                                  "w-5 h-5 rounded-md flex items-center justify-center text-[9px] font-black",
                                  isBuy ? "bg-primary/10 text-primary" : isSell ? "bg-red-500/10 text-red-500" : "bg-muted/50 text-muted-foreground"
                                )}>
                                  {isBuy ? 'B' : isSell ? 'S' : 'H'}
                                </div>
                             </div>
                           );
                        })}
                     </div>
                     <ChevronRight className="w-4 h-4 text-foreground/10 group-hover:text-primary group-hover:translate-x-1 transition-all" />
                  </div>
              </div>
            ))
          )}
        </div>
        
      </CardContent>
    </Card>
  )
}
