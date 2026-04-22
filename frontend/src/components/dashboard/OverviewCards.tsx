"use client"

import React from "react"
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Activity, 
  Percent,
  Loader2
} from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { usePortfolioSummary } from "@/hooks/useApi"
import { Skeleton } from "@/components/ui/skeleton"

export function OverviewCards() {
  const { data, isLoading } = usePortfolioSummary();

  if (isLoading) {
    return (
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="bg-white/5 border-white/5 backdrop-blur-sm">
            <CardContent className="p-6 space-y-4">
              <Skeleton className="h-10 w-10 rounded-xl" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-8 w-32" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const stats = [
    {
      title: "Total Balance",
      value: new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(data?.balance || 0),
      change: data?.total_pnl ? `${data.total_pnl > 0 ? '+' : ''}${data.total_pnl.toFixed(2)}` : "0.00",
      trend: (data?.total_pnl || 0) >= 0 ? "up" : "down",
      icon: DollarSign,
      color: "emerald"
    },
    {
      title: "Current Equity",
      value: new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(data?.equity || 0),
      change: data?.unrealized_pnl ? `${data.unrealized_pnl > 0 ? '+' : ''}${data.unrealized_pnl.toFixed(2)}` : "0.00",
      trend: (data?.unrealized_pnl || 0) >= 0 ? "up" : "down",
      icon: Activity,
      color: "blue"
    },
    {
      title: "Today's PnL",
      value: `${(data?.daily_pnl || 0) >= 0 ? '+' : ''}${new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(data?.daily_pnl || 0)}`,
      change: "Last 24h",
      trend: (data?.daily_pnl || 0) >= 0 ? "up" : "down",
      icon: TrendingUp,
      color: (data?.daily_pnl || 0) >= 0 ? "emerald" : "red"
    },
    {
      title: "Win Rate",
      value: `${data?.win_rate || 0}%`,
      change: `${data?.total_trades || 0} trades`,
      trend: "up",
      icon: Percent,
      color: "emerald"
    }
  ]

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
