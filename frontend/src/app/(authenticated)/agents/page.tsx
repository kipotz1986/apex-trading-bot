"use client"

import React from "react"
import { AgentPerformance } from "@/components/dashboard/AgentPerformance"
import { DecisionLog } from "@/components/dashboard/DecisionLog"
import { DecisionFlowMap } from "@/components/dashboard/DecisionFlowMap"
import { ModeDetailCard } from "@/components/dashboard/ModeDetailCard"
import { ModeBadge } from "@/components/dashboard/ModeBadge"
import { ShieldCheck } from "lucide-react"
import { useConsensusStatus, useBotStatus } from "@/hooks/useApi"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Timer } from "lucide-react"

function BotCycleCountdown() {
  const { data: botStatus } = useBotStatus()
  const [timeLeft, setTimeLeft] = React.useState<number | null>(null)

  React.useEffect(() => {
    if (!botStatus?.last_run_at || !botStatus?.interval) return

    const updateTimer = () => {
      const lastRun = new Date(botStatus.last_run_at!).getTime()
      const intervalMs = botStatus.interval! * 1000
      const nextRun = lastRun + intervalMs
      const now = new Date().getTime()
      
      const diff = Math.max(0, Math.floor((nextRun - now) / 1000))
      setTimeLeft(diff)
    }

    updateTimer()
    const intervalId = setInterval(updateTimer, 1000)

    return () => clearInterval(intervalId)
  }, [botStatus?.last_run_at, botStatus?.interval])

  if (botStatus?.status === "PAUSED") {
    return (
      <div className="flex flex-col items-center justify-center px-6 py-3 rounded-2xl bg-destructive/10 border border-destructive/20 min-w-[160px] glass-card">
        <span className="text-[9px] font-bold text-destructive/50 uppercase tracking-[0.2em] mb-1">Status</span>
        <span className="text-xl font-black text-destructive tracking-tight">PAUSED</span>
      </div>
    )
  }

  const minutes = timeLeft !== null ? Math.floor(timeLeft / 60) : 0
  const seconds = timeLeft !== null ? timeLeft % 60 : 0
  const progress = timeLeft !== null && botStatus?.interval 
    ? (timeLeft / botStatus.interval) * 100 
    : 0

  return (
    <div className="flex flex-col items-center justify-center px-6 py-3 rounded-2xl glass-card border-primary/20 min-w-[160px] relative overflow-hidden group hover:border-primary/40 transition-all duration-300">
      <div className="absolute bottom-0 left-0 w-full h-1 bg-foreground/5">
         <div 
            className="h-full bg-primary/40 transition-all duration-1000 ease-linear shadow-[0_0_10px_rgba(245,158,11,0.5)]"
            style={{ width: `${progress}%` }}
         />
      </div>
      <div className="flex items-center gap-2 mb-1">
         <Timer className="w-3 h-3 text-primary animate-pulse" />
         <span className="text-[9px] font-bold text-primary/50 uppercase tracking-[0.2em]">Next Inference</span>
      </div>
      <div className="text-2xl font-black text-foreground tracking-tighter tabular-nums flex items-baseline gap-0.5 font-heading">
        {timeLeft !== null ? (
          timeLeft > 0 ? (
            <>
                <span className="neon-text">{minutes.toString().padStart(2, '0')}</span>
                <span className="text-primary/20 animate-pulse">:</span>
                <span className="neon-text">{seconds.toString().padStart(2, '0')}</span>
            </>
          ) : (
            <span className="text-sm text-primary animate-pulse font-black uppercase tracking-widest">Processing...</span>
          )
        ) : (
           <span className="text-xs text-foreground/20 italic font-medium">Calibrating...</span>
        )}
      </div>
    </div>
  )
}

function ConsensusLayerCard() {
  const { data, isLoading } = useConsensusStatus()

  const rate = data?.agreement_rate ?? null
  const status = data?.status ?? "Loading..."
  const totalDecisions = data?.total_decisions ?? 0
  const avgScore = data?.avg_consensus_score ?? 0

  const statusColor =
    status === "Synchronized"
      ? "text-primary"
      : status === "Partial Sync"
      ? "text-amber-400"
      : status === "Diverged"
      ? "text-destructive"
      : "text-foreground/30"

  const barColor =
    status === "Synchronized"
      ? "bg-primary/50"
      : status === "Partial Sync"
      ? "bg-amber-400/50"
      : "bg-destructive/40"

  return (
    <div className="p-6 rounded-3xl glass-card space-y-5 relative overflow-hidden group">
      <div className="absolute -top-12 -right-12 w-24 h-24 bg-primary/5 rounded-full blur-3xl group-hover:bg-primary/10 transition-colors" />
      
      <div className="flex items-center justify-between relative z-10">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-primary" />
          <span className="text-[10px] font-bold text-foreground/40 uppercase tracking-[0.2em]">
            Neural Consensus
          </span>
        </div>
        <span className={cn("text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded bg-foreground/5", statusColor)}>
          {isLoading ? "…" : status}
        </span>
      </div>

      <div className="flex justify-between items-baseline relative z-10">
        <span className="text-3xl font-heading font-bold text-foreground neon-text">
          {isLoading ? "—" : rate !== null ? `${rate}%` : "0.0%"}
        </span>
        <span className="text-[9px] font-bold text-foreground/30 uppercase tracking-widest">
          Agreement Delta
        </span>
      </div>

      <div className="h-1.5 w-full bg-foreground/5 rounded-full overflow-hidden border border-border/50 relative z-10">
        <div
          className={cn("h-full rounded-full transition-all duration-700 shadow-[0_0_8px_rgba(245,158,11,0.3)]", barColor)}
          style={{ width: isLoading ? "0%" : `${rate ?? 0}%` }}
        />
      </div>

      <div className="grid grid-cols-2 gap-4 pt-2 relative z-10 border-t border-border/50">
        <div className="flex flex-col">
          <span className="text-[8px] font-bold text-foreground/20 uppercase tracking-[0.2em] mb-1">
            Mean Accuracy
          </span>
          <span className="text-sm font-bold text-foreground/80 font-heading">
            {isLoading ? "—" : `${(avgScore * 100).toFixed(1)}%`}
          </span>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-[8px] font-bold text-foreground/20 uppercase tracking-[0.2em] mb-1">
            Total Validations
          </span>
          <span className="text-sm font-bold text-foreground/80 font-heading">
            {isLoading ? "—" : totalDecisions.toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  )
}

export default function AgentsPage() {
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-3xl md:text-4xl font-heading font-bold tracking-tight text-foreground neon-text">
            Neural Console
          </h1>
          <p className="text-foreground/40 text-sm mt-1 font-medium">Advanced multi-agent reasoning logs and performance metrics.</p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <BotCycleCountdown />
          <ModeBadge variant="compact" />
        </div>
      </div>

      {/* Active Mode Detail — full width, top of page */}
      <div className="animate-in fade-in zoom-in duration-500 delay-150">
        <ModeDetailCard />
      </div>

      {/* Decision Flow Map — full width */}
      <Card className="glass-card overflow-hidden animate-in fade-in duration-500 delay-300">
        <CardContent className="pt-8">
          <DecisionFlowMap />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column: Decision Engine Logs */}
        <div className="lg:col-span-2 space-y-6">
          <DecisionLog />
        </div>

        {/* Right Column: Performance + Consensus */}
        <div className="space-y-6">
          <div className="animate-in slide-in-from-right-4 duration-500 delay-500">
            <AgentPerformance />
          </div>
          <div className="animate-in slide-in-from-right-4 duration-500 delay-700">
            <ConsensusLayerCard />
          </div>
        </div>
      </div>
    </div>
  )
}

