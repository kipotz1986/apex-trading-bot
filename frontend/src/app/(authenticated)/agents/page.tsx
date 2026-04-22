"use client"

import React from "react"
import { AgentPerformance } from "@/components/dashboard/AgentPerformance"
import { DecisionLog } from "@/components/dashboard/DecisionLog"
import { Brain, ShieldCheck, Zap, MessageSquare } from "lucide-react"

export default function AgentsPage() {
  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">AI Agents Console</h1>
          <p className="text-white/40 text-sm mt-1">Real-time performance and reasoning logs from the neural network.</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
         {/* Left Column: Metrics and Logs */}
         <div className="lg:col-span-2 space-y-6">
            <DecisionLog />
         </div>

         {/* Right Column: Performance Summary */}
         <div className="space-y-6">
            <AgentPerformance />
            
            {/* System Health Card */}
            <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/5 space-y-4">
               <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-500" />
                  <span className="text-[10px] font-bold text-white/40 uppercase tracking-widest">Consensus Layer</span>
               </div>
               <div className="flex justify-between items-baseline">
                  <span className="text-2xl font-bold text-white">99.8%</span>
                  <span className="text-xs font-bold text-emerald-500 uppercase">Synchronized</span>
               </div>
               <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500/50 rounded-full w-[99%]" />
               </div>
            </div>
         </div>
      </div>
    </div>
  )
}
