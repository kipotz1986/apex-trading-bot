"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { Zap, ShieldAlert, ShieldCheck, Info } from "lucide-react"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

export function BotControl() {
  const [isRunning, setIsRunning] = useState(true)
  const [mode, setMode] = useState("paper")

  const handleToggle = (checked: boolean) => {
    setIsRunning(checked)
    toast(checked ? "Bot Activated" : "Bot Deactivated", {
      description: checked ? "System is now monitoring markets." : "All algorithms paused.",
      icon: checked ? <Zap className="w-4 h-4 text-emerald-500" /> : <ShieldAlert className="w-4 h-4 text-red-500" />
    })
  }

  const handleModeChange = (newMode: string) => {
    if (newMode === "live") {
      // Logic for 14-day check and win rate gate would go here
      const canGoLive = false // Dummy check
      if (!canGoLive) {
        toast.error("Live Mode Locked", {
          description: "Mandatory 14-day paper trading period not met. Sisa 12 hari lagi."
        })
        return
      }
    }
    setMode(newMode)
    toast.success(`Switched to ${newMode.toUpperCase()} mode`)
  }

  return (
    <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between border-b border-white/5 px-6 py-4">
        <CardTitle className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/40">
          Master Control
        </CardTitle>
        <div className={cn(
          "w-2 h-2 rounded-full",
          isRunning ? "bg-emerald-500 shadow-[0_0_10px_#10b981]" : "bg-red-500 shadow-[0_0_10px_#ef4444]"
        )} />
      </CardHeader>
      
      <CardContent className="p-6 space-y-8">
        {/* Master Toggle */}
        <div className="flex items-center justify-between p-4 rounded-2xl bg-white/[0.03] border border-white/5">
          <div className="space-y-1">
            <Label className="text-sm font-bold text-white tracking-tight">System Operation</Label>
            <p className="text-[10px] font-medium text-white/30 uppercase tracking-widest">
              {isRunning ? "Logic is active" : "System in standby"}
            </p>
          </div>
          <Switch 
            checked={isRunning} 
            onCheckedChange={handleToggle}
            className="data-[state=checked]:bg-emerald-500"
          />
        </div>

        {/* Mode Selection */}
        <div className="space-y-4">
          <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-500/50 pl-1">Execution Mode</Label>
          <RadioGroup 
            value={mode} 
            onValueChange={handleModeChange}
            className="grid grid-cols-2 gap-4"
          >
            <div>
              <RadioGroupItem value="paper" id="paper" className="peer sr-only" />
              <Label
                htmlFor="paper"
                className={cn(
                  "flex flex-col items-center justify-between rounded-xl border-2 border-white/5 bg-transparent p-4 cursor-pointer hover:bg-white/5 transition-all text-white/40 peer-data-[state=checked]:border-emerald-500/50 peer-data-[state=checked]:bg-emerald-500/10 peer-data-[state=checked]:text-white",
                )}
              >
                <ShieldCheck className="mb-3 h-6 w-6" />
                <span className="text-xs font-bold uppercase tracking-tight">Paper Trading</span>
              </Label>
            </div>
            <div>
              <RadioGroupItem value="live" id="live" className="peer sr-only" />
              <Label
                htmlFor="live"
                className={cn(
                  "flex flex-col items-center justify-between rounded-xl border-2 border-white/5 bg-transparent p-4 cursor-pointer hover:bg-white/5 transition-all text-white/40 peer-data-[state=checked]:border-blue-500/50 peer-data-[state=checked]:bg-blue-500/10 peer-data-[state=checked]:text-white",
                )}
              >
                <Zap className="mb-3 h-6 w-6" />
                <span className="text-xs font-bold uppercase tracking-tight">Live Trading</span>
              </Label>
            </div>
          </RadioGroup>
        </div>

        {/* Safety Warning */}
        <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/10 flex gap-3">
          <Info className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
          <p className="text-[10px] leading-relaxed text-amber-500/80 font-medium">
             <b>Safe Mode:</b> 14-day mandatory trial active. Live trading is currently locked until verification period completes.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
