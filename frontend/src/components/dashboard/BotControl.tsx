"use client"

import React, { useCallback, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { Zap, ShieldAlert, ShieldCheck, Info, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { useBotStatus, useToggleBot, useChangeMode } from "@/hooks/useApi"
import { useWebSocket } from "@/hooks/useWebSocket"
import { Skeleton } from "@/components/ui/skeleton"

export function BotControl() {
  const queryClient = useQueryClient()
  const { data: status, isLoading } = useBotStatus()
  const toggleBot = useToggleBot()
  const changeMode = useChangeMode()
  const [switching, setSwitching] = useState(false)

  // Listen for backend broadcast — invalidate everything when profile switches
  const onProfileSwitched = useCallback((data: { mode: string; equity: number | null }) => {
    queryClient.invalidateQueries()
    setSwitching(false)
    toast.success(`Switched to ${data.mode} mode`, {
      description: data.equity !== null ? `Balance: $${data.equity.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "Balance syncing…",
    })
  }, [queryClient])
  useWebSocket("profile_switched", onProfileSwitched)

  if (isLoading) {
    return (
      <Card className="glass-card backdrop-blur-md">
        <CardHeader className="border-b border-border/50 px-6 py-4">
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
        icon: checked ? <Zap className="w-4 h-4 text-primary" /> : <ShieldAlert className="w-4 h-4 text-red-500" />
      })
    } catch (err: any) {
      toast.error("Operation Failed", {
        description: err.response?.data?.detail || "Could not change bot status."
      })
    }
  }

  const handleModeChange = async (newMode: string) => {
    setSwitching(true)
    try {
      await changeMode.mutateAsync(newMode as "live" | "paper")
      // Success toast fires via the profile_switched WS event instead
    } catch (err: any) {
      setSwitching(false)
      const detail = err.response?.data?.detail || "Safety requirements not met."
      const isCredError = detail.toLowerCase().includes("credentials") || detail.toLowerCase().includes("placeholder")
      toast.error(isCredError ? "Live Credentials Required" : "Mode Change Locked", {
        description: detail,
        duration: isCredError ? 8000 : 5000,
      })
    }
  }

  return (
    <Card className="glass-card backdrop-blur-md overflow-hidden relative">
      {/* Profile-switching overlay */}
      {switching && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-black/60 backdrop-blur-sm rounded-[inherit]">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
          <span className="text-[10px] font-bold text-foreground/80 uppercase tracking-widest">Switching Profile…</span>
        </div>
      )}
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/50 px-6 py-4">
        <CardTitle className="text-[11px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
          Master Control
        </CardTitle>
        <div className={cn(
          "w-2 h-2 rounded-full",
          isRunning ? "bg-emerald-500 shadow-[0_0_10px_#10b981]" : "bg-red-500 shadow-[0_0_10px_#ef4444]",
          (toggleBot.isPending || changeMode.isPending || switching) && "animate-pulse"
        )} />
      </CardHeader>
      
      <CardContent className="p-6 space-y-8">
        {/* Master Toggle */}
        <div className="flex items-center justify-between p-4 rounded-2xl bg-muted/30 border border-border/50">
          <div className="space-y-1">
            <Label className="text-sm font-bold text-foreground tracking-tight">System Operation</Label>
            <p className="text-[10px] font-medium text-muted-foreground/80 uppercase tracking-widest">
              {isRunning ? "Logic is active" : "System in standby"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {toggleBot.isPending && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground/60" />}
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
          <Label className="text-[10px] font-bold uppercase tracking-[0.2em] text-primary/50 pl-1">Execution Mode</Label>
          <RadioGroup
            value={mode}
            onValueChange={handleModeChange}
            disabled={changeMode.isPending || switching}
            className="grid grid-cols-2 gap-4"
          >
            <div>
              <RadioGroupItem value="paper" id="paper" className="peer sr-only" />
              <Label
                htmlFor="paper"
                className={cn(
                  "flex flex-col items-center justify-between rounded-xl border-2 border-border/50 bg-transparent p-4 cursor-pointer hover:bg-muted/50 transition-all text-muted-foreground peer-data-[state=checked]:border-primary/50 peer-data-[state=checked]:bg-primary/10 peer-data-[state=checked]:text-foreground",
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
                  "flex flex-col items-center justify-between rounded-xl border-2 border-border/50 bg-transparent p-4 cursor-pointer hover:bg-muted/50 transition-all text-muted-foreground peer-data-[state=checked]:border-blue-500/50 peer-data-[state=checked]:bg-blue-500/10 peer-data-[state=checked]:text-foreground",
                )}
              >
                <Zap className="mb-3 h-6 w-6" />
                <span className="text-xs font-bold uppercase tracking-tight">Live Trading</span>
              </Label>
            </div>
          </RadioGroup>
        </div>

        {/* Safety Warning — only shown while live trading is locked */}
        {status?.is_live_enabled === false && (
          <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/10 flex gap-3">
            <Info className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
            <p className="text-[10px] leading-relaxed text-amber-500/80 font-medium">
               <b>Safe Mode:</b> 14-day mandatory trial active. Live trading is currently locked until verification period completes.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
