"use client"

import React from "react"
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from "recharts"
import { useEquityHistory } from "@/hooks/useApi"
import { Skeleton } from "@/components/ui/skeleton"

export function EquityChart() {
  const { data: history, isLoading } = useEquityHistory();

  if (isLoading) {
    return <Skeleton className="h-[350px] w-full rounded-xl bg-white/5" />;
  }

  // Format data for Recharts: converting ISO string to HH:mm
  const chartData = (history || []).map((item: any) => ({
    ...item,
    time: new Date(item.time).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })
  }));

  return (
    <div className="h-[350px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
          <XAxis 
            dataKey="time" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#ffffff20', fontSize: 10, fontWeight: 600 }}
            dy={10}
          />
          <YAxis 
            domain={['auto', 'auto']} 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#ffffff20', fontSize: 10, fontWeight: 600 }}
            dx={-10}
            tickFormatter={(val) => `$${val}`}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#050B0A', 
              border: '1px solid #10b98130',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 'bold',
              color: '#fff'
            }}
            itemStyle={{ color: '#10b981' }}
            active={true}
            cursor={{ stroke: '#10b98140', strokeWidth: 2 }}
          />
          <Area 
            type="monotone" 
            dataKey="equity" 
            stroke="#10b981" 
            strokeWidth={3}
            fillOpacity={1} 
            fill="url(#colorEquity)" 
            animationDuration={2000}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
