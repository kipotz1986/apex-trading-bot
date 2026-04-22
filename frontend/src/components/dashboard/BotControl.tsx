"use client"

import React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { Zap, ShieldAlert, ShieldCheck, Info, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { useBotStatus, useToggleBot, useChangeMode } from "@/hooks/useApi"
import { Skeleton } from "@/components/ui/skeleton"

export function BotControl() {
  const { data: status, isLoading } = useBotStatus()
  const toggleBot = useToggleBot()
  const changeMode = useChangeMode()

  if (isLoading) {
    return (
      <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
        <CardHeader className="border-b border-white/5 px-6 py-4">
          <Skeleton className="h-4 w-24" />
        </CardHeader>
        <CardContent className="p-6 space-y-8">
          <Skeleton className="h-16 w-full rounded-2xl" />
          <div className="grid grid-cols-2 gap-4">
            <Skeleton className="h-20 w-full rounded-xl" />
            <Skeleton className="h-20 w-full rounded-xl" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const isRunning = status?.status === "NORMAL"
  const mode = status?.mode?.toLowerCase() || "paper"

  const handleToggle = async (checked: boolean) => {
    try {
      await toggleBot.mutateAsync(checked ? "start" : "stop")
      toast.success(checked ? "Bot Activated" : "Bot Deactivated", {
        description: checked ? "System is now monitoring markets." : "All algorithms paused.",
        icon: checked ? <Zap className="w-4 h-4 text-emerald-500" /> : <ShieldAlert className="w-4 h-4 text-red-500" />
      })
    } catch (err: any) {
      toast.error("Operation Failed", {
        description: err.response?.data?.detail || "Could not change bot status."
      })
    }
  }

  const handleModeChange = async (newMode: string) => {
    try {
      await changeMode.mutateAsync(newMode as "live" | "paper")
      toast.success(`Switched to ${newMode.toUpperCase()} mode`)
    } catch (err: any) {
      toast.error("Mode Change Locked", {
        description: err.response?.data?.detail || "Safety requirements not met."
      })
    }
  }

  return (
    <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between border-b border-white/5 px-6 py-4">
        <CardTitle className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/40">
          Master Control
        </CardTitle>
        <div className={cn(
          "w-2 h-2 rounded-full",
          isRunning ? "bg-emerald-500 shadow-[0_0_10px_#10b981]" : "bg-red-500 shadow-[0_0_10px_#ef4444]",
          (toggleBot.isPending || changeMode.isPending) && "animate-pulse"
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
          <div className="flex items-center gap-3">
            {toggleBot.isPending && <Loader2 className="w-4 h-4 animate-spin text-white/20" />}
            <Switch 
              checked={isRunning} 
              onCheckedChange={handleToggle}
              disabled={toggleBot.isPending}
              className="data-[state=checked]:bg-emerald-500"
            />
          </div>
        </div>

        {/* Mode Selection */}
        <div className="space-y-4">
          <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-500/50 pl-1">Execution Mode</Label>
          <RadioGroup 
            value={mode} 
            onValueChange={handleModeChange}
            disabled={changeMode.isPending}
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
