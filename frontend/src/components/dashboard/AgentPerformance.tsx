"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from "recharts"

import { useAgentScores, useLearningStats } from "@/hooks/useApi"
import { AgentScore } from "@/types/api"
import { cn } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"

const STATUS_STYLES: Record<AgentScore["status"], { text: string; bg: string; dot: string }> = {
  CALIBRATING: { text: "text-muted-foreground", bg: "bg-muted/50", dot: "bg-foreground/30" },
  LEARNING: { text: "text-blue-400", bg: "bg-blue-500/10", dot: "bg-blue-400" },
  STABLE: { text: "text-cyan-400", bg: "bg-cyan-500/10", dot: "bg-cyan-400" },
  OPTIMIZED: { text: "text-primary", bg: "bg-primary/10", dot: "bg-emerald-400" },
  STRUGGLING: { text: "text-red-400", bg: "bg-red-500/10", dot: "bg-red-400" },
}

function getBarColor(status: AgentScore["status"], accuracy: number): string {
  if (status === "STRUGGLING") return "#ef4444"
  if (status === "OPTIMIZED") return "#10b981"
  if (status === "STABLE") return "#06b6d4"
  if (status === "LEARNING") return "#3b82f6"
  return "#6366f1" // CALIBRATING
}

export function AgentPerformance() {
  const { data: scores = [], isLoading } = useAgentScores()
  const { data: learningStats } = useLearningStats()

  if (isLoading) {
    return (
      <Card className="glass-card backdrop-blur-md">
        <CardHeader className="flex flex-row items-center justify-between">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </CardHeader>
        <CardContent className="space-y-6">
          <Skeleton className="h-[180px] w-full rounded-lg" />
          <div className="grid grid-cols-2 gap-3">
            {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
          </div>
        </CardContent>
      </Card>
    )
  }

  const agentData = scores.map(s => {
    const accuracy = Math.round(s.accuracy_score * 100)
    return {
      name: s.agent_name.split('_')[0],
      accuracy,
      total: s.total_predictions,
      successful: s.successful_predictions,
      weight: Math.round(s.weight * 100),
      score: s.score,
      status: s.status,
    }
  })

  return (
    <Card className="glass-card backdrop-blur-md">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-[11px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
          Agent Performance
        </CardTitle>
        <Badge variant="outline" className="text-[9px] border-emerald-500/30 text-primary font-black uppercase">
          {learningStats?.model_version || "---"}
        </Badge>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Horizontal bar chart — accuracy per agent */}
        <div className="h-[160px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={agentData} layout="vertical" margin={{ left: 10, right: 30, top: 0, bottom: 0 }}>
              <XAxis type="number" hide domain={[0, 100]} />
              <YAxis
                dataKey="name"
                type="category"
                width={80}
                axisLine={false}
                tickLine={false}
                tick={{ fill: "currentColor", opacity: 0.4, fontSize: 10, fontWeight: 700 }}
              />
              <Bar dataKey="accuracy" radius={[0, 4, 4, 0]} barSize={12}>
                {agentData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getBarColor(entry.status, entry.accuracy)}
                    fillOpacity={0.85}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Per-agent stat cards with dynamic status */}
        <div className="grid grid-cols-1 gap-3">
          {agentData.map((agent) => {
            const style = STATUS_STYLES[agent.status]
            return (
              <div key={agent.name} className="p-3 rounded-xl bg-muted/30 border border-border/50 space-y-2 hover:border-border transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-bold text-foreground uppercase tracking-tight">{agent.name}</span>
                    <span className={cn("flex items-center gap-1.5 text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded", style.bg, style.text)}>
                      <span className={cn("w-1.5 h-1.5 rounded-full", style.dot, agent.status !== "CALIBRATING" && "animate-pulse")} />
                      {agent.status}
                    </span>
                  </div>
                  <span className="text-[9px] font-bold text-muted-foreground/80 uppercase tracking-tight">
                    weight <b className={style.text}>{agent.weight}%</b>
                  </span>
                </div>

                <div className="flex items-end justify-between gap-3">
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold text-foreground tabular-nums">{agent.accuracy}%</span>
                    <span className="text-[10px] text-muted-foreground/80 font-medium">accuracy</span>
                  </div>
                  <div className="text-right text-[10px] text-muted-foreground leading-tight">
                    <div>
                      <b className="text-primary/80">{agent.successful}</b> wins / <b className="text-foreground/80">{agent.total}</b> trades
                    </div>
                    <div className="text-[9px] text-muted-foreground/60">
                      EMA: <span className="font-mono">{agent.score.toFixed(0)}</span>
                    </div>
                  </div>
                </div>

                {/* Inline accuracy bar */}
                <div className="h-1 w-full bg-muted/50 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${agent.accuracy}%`,
                      backgroundColor: getBarColor(agent.status, agent.accuracy),
                      opacity: 0.7,
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>

        {/* Legend for status meanings */}
        <div className="pt-3 border-t border-border/50 space-y-1.5">
          <p className="text-[9px] font-bold text-muted-foreground/80 uppercase tracking-widest mb-2">Status Legend</p>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-foreground/30" /> <b className="text-muted-foreground">CALIBRATING</b> &lt;10 trades
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" /> <b className="text-blue-400">LEARNING</b> &lt;50 trades
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" /> <b className="text-cyan-400">STABLE</b> 45-65% acc
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> <b className="text-primary">OPTIMIZED</b> ≥65% acc
            </div>
            <div className="flex items-center gap-1.5 col-span-2">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" /> <b className="text-red-400">STRUGGLING</b> &lt;45% acc — agent terabaikan saat voting
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
