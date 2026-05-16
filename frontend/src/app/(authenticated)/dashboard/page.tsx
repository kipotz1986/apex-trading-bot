"use client"

import { OverviewCards } from "@/components/dashboard/OverviewCards"
import { EquityChart } from "@/components/dashboard/EquityChart"
import { CandlestickChart } from "@/components/dashboard/CandlestickChart"
import { PositionsTable } from "@/components/dashboard/PositionsTable"
import { BotControl } from "@/components/dashboard/BotControl"
import { ModeBadge } from "@/components/dashboard/ModeBadge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Zap, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useAgentInsights, useOpenPositions } from "@/hooks/useApi"
import { useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

export default function DashboardPage() {
  const queryClient = useQueryClient()
  const [isSyncing, setIsSyncing] = useState(false)
  
  const { data: insights, isLoading: insightsLoading } = useAgentInsights()
  const { data: positions } = useOpenPositions()

  const handleSync = async () => {
    setIsSyncing(true)
    try {
      await queryClient.invalidateQueries()
      toast.success("Dashboard Synchronized", {
        description: "All data metrics updated from server."
      })
    } finally {
      setIsSyncing(false)
    }
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-heading font-bold tracking-tight text-foreground neon-text">
            Performance Overview
          </h1>
          <p className="text-foreground/40 text-sm mt-1 font-medium">Real-time portfolio metrics and AI trading activity.</p>
        </div>
        <div className="flex items-center gap-3">
          <ModeBadge variant="compact" />
          <Button
            onClick={handleSync}
            disabled={isSyncing}
            className="glass-button bg-primary/20 hover:bg-primary/30 text-primary font-bold text-xs gap-2 border-primary/30 shadow-[0_0_20px_rgba(245,158,11,0.15)]"
          >
            {isSyncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4 fill-primary" />}
            RUN SYNC
          </Button>
        </div>
      </div>

      {/* Main Stats */}
      <div className="animate-in fade-in zoom-in duration-500 delay-150 fill-mode-both">
        <OverviewCards />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column: Equity Chart + Candlestick */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="glass-card overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between pb-8 border-b border-white/5">
              <CardTitle className="text-xs font-heading font-bold uppercase tracking-[0.2em] text-primary/80">
                Equity Curve
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <EquityChart />
            </CardContent>
          </Card>

          <Card className="glass-card overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between pb-2 border-b border-white/5">
              <CardTitle className="text-xs font-heading font-bold uppercase tracking-[0.2em] text-primary/80">
                Market Analytics
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <CandlestickChart />
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Control & Insights */}
        <div className="space-y-6">
          <div className="animate-in slide-in-from-right-4 duration-500 delay-300 fill-mode-both">
            <BotControl />
          </div>

          <Card className="glass-card">
            <CardHeader className="border-b border-white/5">
              <CardTitle className="text-[11px] font-heading font-bold uppercase tracking-[0.2em] text-foreground/40">
                AI Intelligence Insight
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
               {insightsLoading ? (
                 <div className="space-y-4">
                   <Skeleton className="h-20 w-full rounded-xl bg-foreground/5" />
                   <Skeleton className="h-4 w-20 bg-foreground/5" />
                   <Skeleton className="h-2 w-full bg-foreground/5" />
                 </div>
               ) : (
                 <>
                   <div className="p-5 rounded-2xl bg-primary/5 border border-primary/20 space-y-3 relative overflow-hidden group">
                      <div className="absolute inset-0 bg-primary/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                      <div className="flex items-center gap-2 relative z-10">
                         <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                         <span className="text-[10px] font-bold text-primary uppercase tracking-[0.2em]">Market Regime</span>
                      </div>
                      <p className="text-sm text-foreground/80 leading-relaxed font-medium relative z-10">
                        {insights?.narrative || "Analyzing market conditions across multiple agents..."}
                      </p>
                   </div>

                   <div className="space-y-5">
                      <h4 className="text-[10px] font-bold text-foreground/30 uppercase tracking-[0.2em]">Agent Confidence Scores</h4>
                      <div className="space-y-4">
                         {[
                           { label: "Technical Analyst", val: insights?.scores.technical || 0, color: "oklch(0.7 0.2 190)" },
                           { label: "Sentiment Analyst", val: insights?.scores.sentiment || 0, color: "oklch(0.7 0.3 320)" },
                           { label: "Fundamental/On-Chain", val: insights?.scores.onchain || 0, color: "oklch(0.769 0.188 70.08)" }
                         ].map(a => (
                           <div key={a.label} className="space-y-2">
                              <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest">
                                 <span className="text-foreground/50">{a.label}</span>
                                 <span style={{ color: a.color }}>{a.val}%</span>
                              </div>
                              <div className="h-1.5 w-full bg-foreground/5 rounded-full overflow-hidden border border-white/5">
                                 <div 
                                    className="h-full rounded-full transition-all duration-1000 ease-out" 
                                    style={{ width: `${a.val}%`, backgroundColor: a.color, boxShadow: `0 0 10px ${a.color}80` }} 
                                 />
                              </div>
                           </div>
                         ))}
                      </div>
                   </div>
                 </>
               )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Positions Section */}
      <Card className="glass-card overflow-hidden animate-in slide-in-from-bottom-4 duration-500 delay-500 fill-mode-both">
        <CardHeader className="flex flex-col md:flex-row md:items-center justify-between border-b border-white/5 px-8 py-6 gap-4">
          <CardTitle className="text-xs font-heading font-bold uppercase tracking-[0.2em] text-primary/80">
            Active Market Exposure
          </CardTitle>
          <div className="flex items-center gap-2">
            <div className="px-3 py-1 rounded-full bg-primary/10 border border-primary/30 text-primary text-[10px] font-black tracking-widest uppercase animate-pulse">
               {positions?.length || 0} Open Positions
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
           <PositionsTable />
        </CardContent>
      </Card>
    </div>
  )
}

