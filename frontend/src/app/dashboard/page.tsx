import { OverviewCards } from "@/components/dashboard/OverviewCards"
import { EquityChart } from "@/components/dashboard/EquityChart"
import { PositionsTable } from "@/components/dashboard/PositionsTable"
import { BotControl } from "@/components/dashboard/BotControl"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ListFilter, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function DashboardPage() {
  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Performance Overview</h1>
          <p className="text-white/40 text-sm mt-1">Real-time portfolio metrics and AI trading activity.</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="bg-white/5 border-white/5 hover:bg-white/10 text-xs gap-2">
            <ListFilter className="w-4 h-4" /> Filter Range
          </Button>
          <Button className="bg-emerald-500 hover:bg-emerald-400 text-black font-bold text-xs gap-2 shadow-[0_0_15px_rgba(16,185,129,0.3)]">
            <Zap className="w-4 h-4 fill-black" /> Run Sync
          </Button>
        </div>
      </div>

      {/* Main Stats */}
      <OverviewCards />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column: Equity Chart */}
        <Card className="lg:col-span-2 bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
          <CardHeader className="flex flex-row items-center justify-between pb-8">
            <CardTitle className="text-sm font-bold uppercase tracking-widest text-emerald-500/80 decoration-emerald-500/20 decoration-2 underline-offset-8">
              Equity Curve
            </CardTitle>
            <div className="flex gap-1">
              {['1D', '1W', '1M', 'ALL'].map(t => (
                <button key={t} className="px-3 py-1 rounded-md text-[10px] font-bold text-white/40 hover:text-white hover:bg-white/5 transition-all">
                  {t}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            <EquityChart />
          </CardContent>
        </Card>

        {/* Right Column: Control & Insights */}
        <div className="space-y-6">
          <BotControl />

          <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
            <CardHeader>
              <CardTitle className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/40">
                AI Insight
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
               <div className="p-4 rounded-xl bg-blue-500/5 border border-blue-500/10 space-y-3">
                  <div className="flex items-center gap-2">
                     <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                     <span className="text-[10px] font-bold text-blue-500 uppercase tracking-widest">Market Regime</span>
                  </div>
                  <p className="text-xs text-white/70 leading-relaxed font-medium">
                    Trend BTC/USDT dominan BULLISH di timeframe 4H. AI mendeteksi akumulasi kuat di area support $63.5k.
                  </p>
               </div>

               <div className="space-y-4">
                  <h4 className="text-[10px] font-bold text-white/30 uppercase tracking-widest">Active Confidence</h4>
                  <div className="space-y-3">
                     {[
                       { label: "Technical", val: 85 },
                       { label: "Sentiment", val: 62 },
                       { label: "On-Chain", val: 45 }
                     ].map(a => (
                       <div key={a.label} className="space-y-1.5">
                          <div className="flex justify-between text-[10px] font-bold uppercase tracking-tighter">
                             <span className="text-white/50">{a.label}</span>
                             <span className="text-emerald-500/80">{a.val}%</span>
                          </div>
                          <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                             <div className="h-full bg-emerald-500/50 rounded-full" style={{ width: `${a.val}%` }} />
                          </div>
                       </div>
                     ))}
                  </div>
               </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Positions Section */}
      <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md overflow-hidden">
        <CardHeader className="flex flex-row items-center justify-between border-b border-white/5 px-8 py-6">
          <CardTitle className="text-sm font-bold uppercase tracking-widest text-emerald-500/80">
            Open Positions
          </CardTitle>
          <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-500 text-[10px] font-black tracking-tighter">
             3 ACTIVE TRADES
          </span>
        </CardHeader>
        <CardContent className="p-0">
           <PositionsTable />
        </CardContent>
      </Card>
    </div>
  )
}
