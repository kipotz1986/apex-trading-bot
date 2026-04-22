"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Brain, Cpu, Database, Network } from "lucide-react"
import { useLearningStats } from "@/hooks/useApi"
import { Skeleton } from "@/components/ui/skeleton"

export default function LearningPage() {
  const { data, isLoading } = useLearningStats()
  
  const stats = [
    { label: "Patterns Learned", val: data?.patterns_learned?.toLocaleString() || "0", icon: Database, color: "blue" },
    { label: "Model Version", val: data?.model_version || "---", icon: Cpu, color: "emerald" },
    { label: "Training Cycles", val: data?.training_cycles || "0h", icon: Network, color: "amber" },
    { label: "RL Reward Score", val: `${(data?.rl_reward_score || 0) > 0 ? '+' : ''}${data?.rl_reward_score || '0.0'}`, icon: Brain, color: "emerald" },
  ]

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex items-center justify-between">
        <div>
           <h1 className="text-3xl font-bold tracking-tight text-white">Self-Learning Pulse</h1>
           <p className="text-white/40 text-sm mt-1">Neural network training metrics and strategy evolution timeline.</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
         {isLoading ? (
            [1, 2, 3, 4].map(i => (
              <Card key={i} className="bg-white/5 border-white/5">
                <CardContent className="p-6 space-y-4">
                  <Skeleton className="h-8 w-8 rounded-lg" />
                  <div className="space-y-2">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-6 w-32" />
                  </div>
                </CardContent>
              </Card>
            ))
         ) : (
           stats.map(item => (
            <Card key={item.label} className="bg-white/5 border-white/5 backdrop-blur-md">
               <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                     <div className={`p-2 rounded-lg bg-${item.color === 'emerald' ? 'emerald' : item.color === 'blue' ? 'blue' : 'amber'}-500/10 border border-${item.color === 'emerald' ? 'emerald' : item.color === 'blue' ? 'blue' : 'amber'}-500/20`}>
                        <item.icon className={`w-4 h-4 text-${item.color === 'emerald' ? 'emerald' : item.color === 'blue' ? 'blue' : 'amber'}-500`} />
                     </div>
                  </div>
                  <h3 className="text-white/40 text-[10px] font-bold uppercase tracking-widest">{item.label}</h3>
                  <p className="text-2xl font-bold text-white tracking-tight">{item.val}</p>
               </CardContent>
            </Card>
          ))
         )}
      </div>

      <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
         <CardHeader>
           <CardTitle className="text-sm font-bold uppercase tracking-widest text-emerald-500/80">
             Strategy Evolution Timeline
           </CardTitle>
         </CardHeader>
         <CardContent className="h-[400px] flex items-center justify-center border border-dashed border-white/10 rounded-2xl m-6 mt-0">
            <div className="text-center space-y-2 opacity-20">
               <Brain className="w-12 h-12 mx-auto" />
               <p className="text-xs font-bold uppercase tracking-widest">Neural Projection Loading...</p>
            </div>
         </CardContent>
      </Card>
    </div>
  )
}
