"use client"

import { useState } from "react"
import { Shield, Scale, Zap, Flame, Skull, Info, ChevronDown, Settings as SettingsIcon, Check, Loader2 } from "lucide-react"
import { useActiveModeProfile, useModeProfiles, useSetModeProfile, type ModeProfile } from "@/hooks/useApi"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  Shield, Scale, Zap, Flame, Skull,
}

const COLORS: Record<string, { bg: string; border: string; text: string; gradient: string; ring: string }> = {
  emerald: { bg: "bg-primary/10", border: "border-emerald-500/30", text: "text-primary", gradient: "from-emerald-500/20 to-transparent", ring: "ring-primary/50" },
  blue: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400", gradient: "from-blue-500/20 to-transparent", ring: "ring-blue-500/50" },
  amber: { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400", gradient: "from-amber-500/20 to-transparent", ring: "ring-amber-500/50" },
  orange: { bg: "bg-orange-500/10", border: "border-orange-500/30", text: "text-orange-400", gradient: "from-orange-500/20 to-transparent", ring: "ring-orange-500/50" },
  red: { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400", gradient: "from-red-500/20 to-transparent", ring: "ring-red-500/50" },
}

function formatValue(value: string, unit: string): string {
  switch (unit) {
    case "percent":
      return `${value}%`
    case "x":
      return `${value}×`
    case "score":
      return value
    case "count":
      return value
    case "multiplier":
      return `${value}×`
    case "toggle":
      return value === "true" ? "Aktif" : "Mati"
    default:
      return value
  }
}

export function ModeDetailCard() {
  const { data: profile, isLoading } = useActiveModeProfile()
  const { data: modeData } = useModeProfiles()
  const setMode = useSetModeProfile()

  const [showDetails, setShowDetails] = useState(false)
  const [showSelector, setShowSelector] = useState(false)

  const handleSelectMode = async (slug: string) => {
    if (slug === profile?.slug) {
      setShowSelector(false)
      return
    }
    try {
      const result = await setMode.mutateAsync(slug)
      toast.success(`Mode aktif: ${result.name}`, { description: result.tagline })
      setShowSelector(false)
    } catch (e: any) {
      toast.error("Mode change failed", {
        description: e.response?.data?.detail || "Could not switch bot mode.",
      })
    }
  }

  if (isLoading || !profile) {
    return (
      <Card className="glass-card backdrop-blur-md">
        <CardContent className="p-6 space-y-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
    )
  }

  const Icon = ICONS[profile.icon] || Shield
  const color = COLORS[profile.color] || COLORS.blue

  return (
    <Card className={cn("backdrop-blur-md overflow-hidden relative", color.bg, color.border, "border")}>
      <div className={cn("absolute top-0 right-0 w-72 h-72 rounded-full blur-3xl opacity-30 pointer-events-none bg-gradient-radial", color.gradient)} />

      <CardHeader className="relative">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-4 min-w-0 flex-1">
            <div className={cn("p-3 rounded-xl border", color.bg, color.border, "shrink-0")}>
              <Icon className={cn("w-6 h-6", color.text)} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Active Bot Mode</span>
                <span className={cn("text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded", color.bg, color.text)}>
                  Level {profile.risk_level}/5
                </span>
              </div>
              <CardTitle className={cn("text-2xl font-bold", color.text)}>{profile.name}</CardTitle>
              <p className="text-xs text-foreground/80 mt-1 leading-relaxed">{profile.tagline}</p>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSelector(!showSelector)}
              className={cn(
                "text-xs font-bold border-border text-foreground/90 hover:text-foreground gap-2",
                showSelector && cn(color.border, color.text),
              )}
            >
              <SettingsIcon className="w-3.5 h-3.5" />
              {showSelector ? "Tutup" : "Ubah Mode"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDetails(!showDetails)}
              className="text-xs font-bold border-border text-foreground/90 hover:text-foreground gap-2"
            >
              {showDetails ? "Sembunyikan Detail" : "Lihat Detail"}
              <ChevronDown className={cn("w-3.5 h-3.5 transition-transform duration-300", showDetails && "rotate-180")} />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="relative space-y-0">
        {/* Plain-language description always visible */}
        <div className={cn("p-4 rounded-xl border", "bg-muted/20", "border-border/50")}>
          <div className="flex gap-3">
            <Info className="w-4 h-4 text-muted-foreground/80 shrink-0 mt-0.5" />
            <p className="text-xs text-foreground/90 leading-relaxed">{profile.description}</p>
          </div>
        </div>

        {/* Mode selector — collapsible */}
        <div
          className={cn(
            "grid transition-all duration-500 ease-in-out",
            showSelector ? "grid-rows-[1fr] opacity-100 mt-4" : "grid-rows-[0fr] opacity-0 mt-0",
          )}
        >
          <div className="overflow-hidden">
            <div className="space-y-2 pt-2">
              <h3 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-3">Pilih Bot Mode</h3>
              {modeData?.profiles.map((p: ModeProfile) => {
                const isActive = p.slug === profile.slug
                const PIcon = ICONS[p.icon] || Shield
                const pColor = COLORS[p.color] || COLORS.blue
                return (
                  <button
                    key={p.slug}
                    onClick={() => handleSelectMode(p.slug)}
                    disabled={setMode.isPending}
                    className={cn(
                      "w-full text-left rounded-xl border-2 p-3 transition-all hover:bg-muted/30 disabled:opacity-50 disabled:cursor-not-allowed",
                      isActive ? cn(pColor.border, pColor.bg, "ring-1", pColor.ring) : "border-border/50 bg-transparent",
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn("p-1.5 rounded-lg border shrink-0", pColor.bg, pColor.border)}>
                        <PIcon className={cn("w-4 h-4", pColor.text)} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={cn("text-sm font-bold", isActive ? pColor.text : "text-foreground")}>
                            {p.name}
                          </span>
                          <span className="text-[9px] font-bold text-muted-foreground/80 uppercase tracking-widest">
                            L{p.risk_level}/5
                          </span>
                          {isActive && (
                            <span className={cn("flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest", pColor.text)}>
                              <Check className="w-3 h-3" /> Aktif
                            </span>
                          )}
                          {setMode.isPending && setMode.variables === p.slug && (
                            <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
                          )}
                        </div>
                        <p className={cn("text-[11px] leading-relaxed", isActive ? "text-foreground/90" : "text-muted-foreground")}>
                          {p.tagline}
                        </p>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* Parameter detail — collapsible */}
        <div
          className={cn(
            "grid transition-all duration-500 ease-in-out",
            showDetails ? "grid-rows-[1fr] opacity-100 mt-4" : "grid-rows-[0fr] opacity-0 mt-0",
          )}
        >
          <div className="overflow-hidden">
            <div className="pt-2">
              <h3 className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-3">Parameter Detail</h3>
              <div className="grid gap-3 md:grid-cols-2">
                {profile.param_details.map((param) => (
                  <div
                    key={param.key}
                    className="p-3 rounded-lg bg-muted/20 border border-border/50 hover:border-border transition-colors"
                  >
                    <div className="flex items-baseline justify-between gap-2 mb-1">
                      <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                        {param.label}
                      </span>
                      <span className={cn("text-base font-bold font-mono", color.text)}>
                        {formatValue(param.value, param.unit)}
                      </span>
                    </div>
                    <p className="text-[10px] text-muted-foreground leading-relaxed">{param.explanation}</p>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-muted-foreground/80 italic pt-3 mt-3 border-t border-border/50">
                💡 Mode bisa diubah dari tombol <b className="text-muted-foreground">Ubah Mode</b> di atas, atau di halaman <b className="text-muted-foreground">Settings → Bot Mode</b>.
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
