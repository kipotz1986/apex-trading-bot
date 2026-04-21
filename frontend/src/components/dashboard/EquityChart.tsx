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

const data = [
  { time: "00:00", equity: 10000 },
  { time: "04:00", equity: 10050 },
  { time: "08:00", equity: 10120 },
  { time: "12:00", equity: 10080 },
  { time: "16:00", equity: 10150 },
  { time: "20:00", equity: 10210 },
  { time: "23:59", equity: 10240 },
]

export function EquityChart() {
  return (
    <div className="h-[350px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
            domain={['dataMin - 100', 'dataMax + 100']} 
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
