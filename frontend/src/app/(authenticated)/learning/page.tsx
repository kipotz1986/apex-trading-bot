"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Brain, Cpu, Database, Network, GitCommit, GitPullRequest, GitMerge } from "lucide-react"
import { useLearningStats, useStrategyEvolution } from "@/hooks/useApi"
import { Skeleton } from "@/components/ui/skeleton"
import { fmtDateShortTime } from "@/lib/dateFormat"

export default function LearningPage() {
  const { data: statsData, isLoading: statsLoading } = useLearningStats()
  const { data: timelineData, isLoading: timelineLoading } = useStrategyEvolution()
  
  const stats = [
    { label: "Patterns Learned", val: statsData?.patterns_learned?.toLocaleString() || "0", icon: Database, color: "blue" },
    { label: "Model Version", val: statsData?.model_version || "---", icon: Cpu, color: "emerald" },
    { label: "Training Cycles", val: statsData?.training_cycles || "0h", icon: Network, color: "amber" },
    { label: "RL Reward Score", val: `${(statsData?.rl_reward_score || 0) > 0 ? '+' : ''}${statsData?.rl_reward_score || '0.0'}`, icon: Brain, color: "emerald" },
  ]

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex items-center justify-between">
        <div>
           <h1 className="text-3xl font-bold tracking-tight text-foreground">Self-Learning Pulse</h1>
           <p className="text-muted-foreground text-sm mt-1">Neural network training metrics and strategy evolution timeline.</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
         {statsLoading ? (
            [1, 2, 3, 4].map(i => (
              <Card key={i} className="bg-muted/50 border-border/50">
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
            <Card key={item.label} className="bg-muted/50 border-border/50 backdrop-blur-md">
               <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                     <div className={`p-2 rounded-lg bg-${item.color === 'emerald' ? 'emerald' : item.color === 'blue' ? 'blue' : 'amber'}-500/10 border border-${item.color === 'emerald' ? 'emerald' : item.color === 'blue' ? 'blue' : 'amber'}-500/20`}>
                        <item.icon className={`w-4 h-4 text-${item.color === 'emerald' ? 'emerald' : item.color === 'blue' ? 'blue' : 'amber'}-500`} />
                     </div>
                  </div>
                  <h3 className="text-muted-foreground text-[10px] font-bold uppercase tracking-widest">{item.label}</h3>
                  <p className="text-2xl font-bold text-foreground tracking-tight">{item.val}</p>
               </CardContent>
            </Card>
          ))
         )}
      </div>

      <Card className="glass-card backdrop-blur-md">
         <CardHeader>
           <CardTitle className="text-sm font-bold uppercase tracking-widest text-primary/80">
             Strategy Evolution Timeline
           </CardTitle>
         </CardHeader>
         <CardContent className="m-6 mt-0 p-0">
            {timelineLoading ? (
               <div className="h-[400px] flex items-center justify-center border border-dashed border-border rounded-2xl">
                  <div className="text-center space-y-2 opacity-20">
                     <Brain className="w-12 h-12 mx-auto animate-pulse" />
                     <p className="text-xs font-bold uppercase tracking-widest">Neural Projection Loading...</p>
                  </div>
               </div>
            ) : timelineData && timelineData.length > 0 ? (
               <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-white/10 before:to-transparent">
                  {timelineData.map((event, i) => (
                     <div key={event.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                        <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-[#050B0A] bg-muted/50 text-foreground shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
                           {event.event_type === 'model_training' ? <GitMerge className="w-4 h-4 text-primary" /> : 
                            event.event_type === 'strong_consensus' ? <GitCommit className="w-4 h-4 text-amber-500" /> :
                            <GitPullRequest className="w-4 h-4 text-blue-500" />}
                        </div>
                        <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-muted/20 border border-border/50 hover:border-border transition-colors p-4 rounded-xl">
                           <div className="flex items-center justify-between mb-1">
                              <span className="text-[10px] font-bold text-muted-foreground tracking-widest uppercase">{fmtDateShortTime(event.timestamp)}</span>
                              {event.metrics && (
                                 <span className="text-[9px] font-black text-primary/80 bg-primary/10 px-2 py-0.5 rounded">
                                    {Object.entries(event.metrics).map(([k,v]) => `${v}`).join(', ')}
                                 </span>
                              )}
                           </div>
                           <h4 className="text-sm font-bold text-foreground mb-2">{event.title}</h4>
                           <p className="text-xs text-muted-foreground">{event.description}</p>
                        </div>
                     </div>
                  ))}
               </div>
            ) : (
               <div className="h-[400px] flex items-center justify-center border border-dashed border-border rounded-2xl">
                  <div className="text-center space-y-2 opacity-20">
                     <Brain className="w-12 h-12 mx-auto" />
                     <p className="text-xs font-bold uppercase tracking-widest">No Evolution Events Found</p>
                  </div>
               </div>
            )}
         </CardContent>
      </Card>
    </div>
  )
}
