"use client"

import { Shield, Scale, Zap, Flame, Skull } from "lucide-react"
import { useActiveModeProfile } from "@/hooks/useApi"
import { cn } from "@/lib/utils"

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  Shield, Scale, Zap, Flame, Skull,
}

const COLORS: Record<string, { bg: string; border: string; text: string }> = {
  emerald: { bg: "bg-primary/10", border: "border-emerald-500/30", text: "text-primary" },
  blue: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400" },
  amber: { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400" },
  orange: { bg: "bg-orange-500/10", border: "border-orange-500/30", text: "text-orange-400" },
  red: { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400" },
}

interface ModeBadgeProps {
  variant?: "compact" | "full"
  className?: string
}

export function ModeBadge({ variant = "compact", className }: ModeBadgeProps) {
  const { data: profile, isLoading } = useActiveModeProfile()

  if (isLoading || !profile) {
    return (
      <div className={cn("flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted/50 border border-border", className)}>
        <span className="text-[10px] font-bold text-muted-foreground/80 uppercase tracking-widest">Loading mode…</span>
      </div>
    )
  }

  const Icon = ICONS[profile.icon] || Shield
  const color = COLORS[profile.color] || COLORS.blue

  if (variant === "compact") {
    return (
      <div
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-lg border",
          color.bg, color.border,
          className,
        )}
        title={profile.tagline}
      >
        <Icon className={cn("w-3.5 h-3.5", color.text)} />
        <span className={cn("text-[10px] font-black uppercase tracking-widest", color.text)}>
          {profile.name}
        </span>
        <span className="text-[9px] font-bold text-muted-foreground/80">L{profile.risk_level}/5</span>
      </div>
    )
  }

  // full variant
  return (
    <div className={cn("p-4 rounded-xl border", color.bg, color.border, className)}>
      <div className="flex items-start gap-3">
        <div className={cn("p-2 rounded-lg border", color.bg, color.border)}>
          <Icon className={cn("w-5 h-5", color.text)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={cn("text-sm font-bold", color.text)}>{profile.name}</span>
            <span className="text-[9px] font-bold text-muted-foreground/80 uppercase tracking-widest">Level {profile.risk_level}/5</span>
          </div>
          <p className="text-[11px] text-foreground/80 leading-relaxed">{profile.tagline}</p>
        </div>
      </div>
    </div>
  )
}
