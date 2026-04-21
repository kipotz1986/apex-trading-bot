"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Brain, Cpu, Database, Network } from "lucide-react"

export default function LearningPage() {
  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex items-center justify-between">
        <div>
           <h1 className="text-3xl font-bold tracking-tight text-white">Self-Learning Pulse</h1>
           <p className="text-white/40 text-sm mt-1">Neural network training metrics and strategy evolution timeline.</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
         {[
           { label: "Patterns Learned", val: "1,242", icon: Database, color: "blue" },
           { label: "Model Version", val: "v4.2.1-λ", icon: Cpu, color: "emerald" },
           { label: "Training Cycles", val: "840h", icon: Network, color: "amber" },
           { label: "RL Reward Score", val: "+24.5", icon: Brain, color: "emerald" },
         ].map(item => (
           <Card key={item.label} className="bg-white/5 border-white/5 backdrop-blur-md">
              <CardContent className="p-6">
                 <div className="flex items-center justify-between mb-4">
                    <div className={`p-2 rounded-lg bg-${item.color}-500/10 border border-${item.color}-500/20`}>
                       <item.icon className={`w-4 h-4 text-${item.color}-500`} />
                    </div>
                 </div>
                 <h3 className="text-white/40 text-[10px] font-bold uppercase tracking-widest">{item.label}</h3>
                 <p className="text-2xl font-bold text-white tracking-tight">{item.val}</p>
              </CardContent>
           </Card>
         ))}
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
