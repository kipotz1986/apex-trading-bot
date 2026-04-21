"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from "recharts"

const agentData = [
  { name: "Technical", score: 85, weight: "40%", status: "OPTIMIZED" },
  { name: "Sentiment", score: 62, weight: "25%", status: "STABLE" },
  { name: "On-Chain", score: 45, weight: "20%", status: "LEARNING" },
  { name: "Risk Guard", score: 98, weight: "15%", status: "CRITICAL" },
]

export function AgentPerformance() {
  return (
    <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/40">
          Agent Performance
        </CardTitle>
        <Badge variant="outline" className="text-[9px] border-emerald-500/30 text-emerald-500 font-black">
          V2.1.0-STABLE
        </Badge>
      </CardHeader>
      
      <CardContent className="space-y-6">
        <div className="h-[180px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={agentData} layout="vertical" margin={{ left: -20, right: 20 }}>
              <XAxis type="number" hide />
              <YAxis 
                dataKey="name" 
                type="category" 
                axisLine={false} 
                tickLine={false}
                tick={{ fill: "#ffffff40", fontSize: 10, fontWeight: 700 }}
              />
              <Bar dataKey="score" radius={[0, 4, 4, 0]} barSize={12}>
                {agentData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={entry.score > 80 ? "#10b981" : entry.score > 50 ? "#3b82f6" : "#6366f1"} 
                    fillOpacity={0.8}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {agentData.map((agent) => (
            <div key={agent.name} className="p-3 rounded-xl bg-white/[0.03] border border-white/5 space-y-2">
              <div className="flex justify-between items-start">
                <span className="text-[10px] font-bold text-white/50 uppercase">{agent.name}</span>
                <span className="text-[9px] font-black text-emerald-500/60 bg-emerald-500/5 px-1.5 rounded">{agent.weight}</span>
              </div>
              <div className="flex items-end justify-between">
                <span className="text-sm font-bold text-white">{agent.score}%</span>
                <span className={cn(
                  "text-[8px] font-bold tracking-tighter",
                  agent.status === 'OPTIMIZED' ? "text-emerald-500" : "text-blue-400"
                )}>
                  {agent.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

import { cn } from "@/lib/utils"
