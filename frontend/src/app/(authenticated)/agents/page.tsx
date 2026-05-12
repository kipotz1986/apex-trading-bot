"use client"

import React from "react"
import { AgentPerformance } from "@/components/dashboard/AgentPerformance"
import { DecisionLog } from "@/components/dashboard/DecisionLog"
import { DecisionFlowMap } from "@/components/dashboard/DecisionFlowMap"
import { ModeDetailCard } from "@/components/dashboard/ModeDetailCard"
import { ModeBadge } from "@/components/dashboard/ModeBadge"
import { ShieldCheck } from "lucide-react"
import { useConsensusStatus } from "@/hooks/useApi"
import { cn } from "@/lib/utils"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

function ConsensusLayerCard() {
  const { data, isLoading } = useConsensusStatus()

  const rate = data?.agreement_rate ?? null
  const status = data?.status ?? "Loading..."
  const totalDecisions = data?.total_decisions ?? 0
  const avgScore = data?.avg_consensus_score ?? 0

  const statusColor =
    status === "Synchronized"
      ? "text-emerald-500"
      : status === "Partial Sync"
      ? "text-amber-400"
      : status === "Diverged"
      ? "text-red-400"
      : "text-white/30"

  const barColor =
    status === "Synchronized"
      ? "bg-emerald-500/50"
      : status === "Partial Sync"
      ? "bg-amber-400/50"
      : "bg-red-400/40"

  return (
    <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-500" />
          <span className="text-[10px] font-bold text-white/40 uppercase tracking-widest">
            Consensus Layer
          </span>
        </div>
        <span className={cn("text-[9px] font-black uppercase tracking-widest", statusColor)}>
          {isLoading ? "…" : status}
        </span>
      </div>

      <div className="flex justify-between items-baseline">
        <span className="text-2xl font-bold text-white">
          {isLoading ? "—" : rate !== null ? `${rate}%` : "N/A"}
        </span>
        <span className="text-[9px] font-bold text-white/30 uppercase">
          Agent Agreement
        </span>
      </div>

      <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-700", barColor)}
          style={{ width: isLoading ? "0%" : `${rate ?? 0}%` }}
        />
      </div>

      <div className="grid grid-cols-2 gap-2 pt-1">
        <div className="flex flex-col">
          <span className="text-[8px] font-bold text-white/20 uppercase tracking-widest">
            Avg Score
          </span>
          <span className="text-xs font-bold text-white/60">
            {isLoading ? "—" : `${(avgScore * 100).toFixed(1)}%`}
          </span>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-[8px] font-bold text-white/20 uppercase tracking-widest">
            Total Decisions
          </span>
          <span className="text-xs font-bold text-white/60">
            {isLoading ? "—" : totalDecisions}
          </span>
        </div>
      </div>
    </div>
  )
}

export default function AgentsPage() {
  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">AI Agents Console</h1>
          <p className="text-white/40 text-sm mt-1">Real-time performance and reasoning logs from the neural network.</p>
        </div>
        <ModeBadge variant="compact" />
      </div>

      {/* Active Mode Detail — full width, top of page */}
      <ModeDetailCard />

      {/* Decision Flow Map — full width */}
      <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
        <CardContent className="pt-6">
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
          <AgentPerformance />
          <ConsensusLayerCard />
        </div>
      </div>
    </div>
  )
}
