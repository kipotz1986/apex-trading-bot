"use client"

import React from "react"
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Activity, 
  BarChart3,
  Percent
} from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"

const stats = [
  {
    title: "Total Balance",
    value: "$10,240.50",
    change: "+2.5%",
    trend: "up",
    icon: DollarSign,
    color: "emerald"
  },
  {
    title: "Current Equity",
    value: "$10,180.20",
    change: "-$60.30",
    trend: "down",
    icon: Activity,
    color: "blue"
  },
  {
    title: "Today's PnL",
    value: "+$245.00",
    change: "+1.2%",
    trend: "up",
    icon: TrendingUp,
    color: "emerald"
  },
  {
    title: "Win Rate",
    value: "64.5%",
    change: "+2.1%",
    trend: "up",
    icon: Percent,
    color: "emerald"
  }
]

export function OverviewCards() {
  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat, i) => (
        <Card key={i} className="bg-white/5 border-white/5 backdrop-blur-sm hover:border-emerald-500/20 transition-all duration-300 group">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className={`p-2 rounded-xl bg-${stat.color}-500/10 border border-${stat.color}-500/20 group-hover:scale-110 transition-transform`}>
                <stat.icon className={`w-5 h-5 text-${stat.color}-500`} />
              </div>
              <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full ${stat.trend === 'up' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'} text-[10px] font-bold uppercase tracking-wider`}>
                {stat.trend === 'up' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {stat.change}
              </div>
            </div>
            
            <div className="space-y-1">
              <h3 className="text-white/40 text-[10px] font-bold uppercase tracking-widest">{stat.title}</h3>
              <p className="text-2xl font-bold text-white tracking-tight leading-none">
                {stat.value}
              </p>
            </div>
            
            {/* Decoration Sparkline Placeholder */}
            <div className="mt-4 h-1 w-full bg-white/5 rounded-full overflow-hidden">
               <div 
                 className={`h-full bg-${stat.color}-500/40 rounded-full transition-all duration-1000`} 
                 style={{ width: `${Math.floor(Math.random() * 40) + 40}%` }}
               />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
