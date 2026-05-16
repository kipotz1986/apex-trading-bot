"use client"

import React from "react"
import {
  BarChart2, Newspaper, Radio,
  TrendingUp, Globe, MessageSquare,
  GitMerge, ShieldCheck, Zap,
  Brain, ChevronRight,
} from "lucide-react"
import { useAgentDecisions, useBotStatus, useTradingSymbols } from "@/hooks/useApi"
import { useWebSocket } from "@/hooks/useWebSocket"
import { fmtDateTime } from "@/lib/dateFormat"

// ─── helpers ──────────────────────────────────────────────────────────────────
function getSig(obj: any): string {
  if (!obj) return "NEUTRAL"
  return typeof obj === "string" ? obj : (obj?.signal ?? "NEUTRAL")
}

function getConf(obj: any): number {
  if (!obj || typeof obj === "string") return 0
  return Number(obj?.confidence ?? 0)
}

function sigHex(sig: string): string {
  const s = (sig || "").toUpperCase()
  if (s.includes("BUY") || s.includes("LONG"))  return "#10b981"
  if (s.includes("SELL") || s.includes("SHORT")) return "#ef4444"
  return "#f59e0b"
}

function sigShort(sig: string): string {
  const s = (sig || "").toUpperCase()
  if (s.includes("STRONG_BUY"))  return "S.BUY"
  if (s.includes("BUY") || s.includes("LONG"))   return "BUY"
  if (s.includes("STRONG_SELL")) return "S.SELL"
  if (s.includes("SELL") || s.includes("SHORT")) return "SELL"
  return "NEUTRAL"
}

function actionLabel(action: string): string {
  const a = (action || "").toUpperCase()
  if (a.includes("LONG"))  return "LONG"
  if (a.includes("SHORT")) return "SHORT"
  return "HOLD"
}

// Derive risk verdict from reasoning text + action
function riskVerdict(dec: AgentDecisionLike): "APPROVED" | "REDUCED" | "REJECTED" | "PASS" {
  const r = (dec.reasoning || "").toUpperCase()
  if (r.includes("REJECTED BY RISK MANAGER") || r.includes("CRITICAL OVERRIDE")) return "REJECTED"
  if (r.includes("SIZE REDUCED") || r.includes("RISK MANAGER: SIZE")) return "REDUCED"
  const a = (dec.action || "").toUpperCase()
  if (a.includes("LONG") || a.includes("SHORT")) return "APPROVED"
  return "PASS"
}

function riskHex(v: ReturnType<typeof riskVerdict>): string {
  if (v === "REJECTED") return "#ef4444"
  if (v === "REDUCED")  return "#f59e0b"
  if (v === "APPROVED") return "#10b981"
  return "#6b7280"
}

interface AgentDecisionLike {
  id?: number
  symbol: string
  action: string
  confidence?: number
  consensus_score?: number
  market_regime?: string
  reasoning?: string
  agent_signals?: Record<string, any>
  timestamp?: string
}

// ─── small reusable pieces ────────────────────────────────────────────────────
function Arrow({ active, hex }: { active: boolean; hex: string }) {
  return (
    <div
      className="flex items-center justify-center shrink-0"
      style={{ width: 18, color: active ? "#fbbf24" : `${hex}88` }}
    >
      <ChevronRight size={14} strokeWidth={2.5} />
    </div>
  )
}

function AgentBadge({
  Icon, label, sig, conf, dim, active,
}: {
  Icon: React.ComponentType<{ size?: number; strokeWidth?: number }>
  label: string
  sig: string
  conf: number
  dim: boolean
  active: boolean
}) {
  const hex = dim ? "#374151" : sigHex(sig)
  return (
    <div
      className="flex flex-col items-center justify-center rounded-md px-1.5 py-1 min-w-0 transition-colors"
      style={{
        width: 64,
        height: 50,
        background: active ? `${hex}1f` : `${hex}10`,
        border: `1px solid ${hex}${active ? "66" : "33"}`,
      }}
      title={`${label}: ${sigShort(sig)} (${(conf * 100).toFixed(0)}%)`}
    >
      <div style={{ color: hex, lineHeight: 0 }}>
        <Icon size={12} strokeWidth={2} />
      </div>
      <div className="text-[7.5px] font-bold uppercase tracking-wide mt-0.5"
           style={{ color: "rgba(255,255,255,0.55)" }}>
        {label}
      </div>
      <div className="text-[8px] font-extrabold leading-none mt-0.5" style={{ color: hex }}>
        {dim ? "—" : sigShort(sig)}
      </div>
    </div>
  )
}

// ─── per-symbol row ───────────────────────────────────────────────────────────
function SymbolRow({
  symbol,
  dec,
  active,
  currentStep,
}: {
  symbol: string
  dec: AgentDecisionLike | null
  active: boolean
  currentStep: string | null
}) {
  const noData = !dec
  const techSig = getSig(dec?.agent_signals?.technical)
  const fundSig = getSig(dec?.agent_signals?.fundamental)
  const sentSig = getSig(dec?.agent_signals?.sentiment)
  const techConf = getConf(dec?.agent_signals?.technical)
  const fundConf = getConf(dec?.agent_signals?.fundamental)
  const sentConf = getConf(dec?.agent_signals?.sentiment)

  const consensus = Number(dec?.consensus_score ?? 0)
  const confidence = Number(dec?.confidence ?? 0)
  const action = dec?.action ?? "HOLD"
  const finalAction = actionLabel(action)
  const finalHex = noData ? "#374151" : sigHex(action)
  const verdict = dec ? riskVerdict(dec) : "PASS"
  const verdictHex = noData ? "#374151" : riskHex(verdict)

  // active sub-step matters only for this row when it IS the active symbol
  const stepActive = (step: string) => active && currentStep === step
  const inputActive     = stepActive("fetching_data")
  const agentsActive    = stepActive("analyzing_agents")
  const consensusActive = stepActive("calculating_consensus")
  const riskActive      = stepActive("evaluating_risk")
  const decisionActive  = stepActive("finalizing_decision")

  const rowBg = active ? "rgba(251,191,36,0.06)" : "transparent"
  const rowBorder = active ? "rgba(251,191,36,0.4)" : "rgba(255,255,255,0.05)"

  return (
    <div
      className="grid items-center gap-2 px-3 py-2 rounded-lg transition-colors"
      style={{
        gridTemplateColumns: "92px 1fr 1fr 1fr 1fr 1fr",
        background: rowBg,
        border: `1px solid ${rowBorder}`,
        animation: active ? "rowPulse 2s ease-in-out infinite" : undefined,
      }}
    >
      {/* SYMBOL */}
      <div className="flex items-center gap-1.5">
        <span
          className="text-[10px] font-extrabold tracking-wide px-2 py-1 rounded"
          style={{
            color: "#fff",
            background: active ? "rgba(251,191,36,0.18)" : "rgba(255,255,255,0.06)",
            border: `1px solid ${active ? "rgba(251,191,36,0.5)" : "rgba(255,255,255,0.1)"}`,
          }}
        >
          {symbol.split("/")[0]}
        </span>
        {active && (
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-70" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-amber-400" />
          </span>
        )}
      </div>

      {/* DATA INPUTS — 3 small icons */}
      <div className="flex items-center gap-1 justify-start">
        {[
          { Icon: BarChart2,    title: "Market Prices" },
          { Icon: Newspaper,    title: "News & Events" },
          { Icon: Radio,        title: "Social Signals" },
        ].map(({ Icon, title }) => (
          <div
            key={title}
            title={title}
            className="flex items-center justify-center rounded"
            style={{
              width: 22, height: 22,
              background: inputActive ? "rgba(251,191,36,0.18)" : "rgba(99,102,241,0.1)",
              border: `1px solid ${inputActive ? "rgba(251,191,36,0.5)" : "rgba(99,102,241,0.25)"}`,
              color: inputActive ? "#fbbf24" : "#818cf8",
            }}
          >
            <Icon size={11} strokeWidth={2} />
          </div>
        ))}
        <Arrow active={agentsActive} hex={finalHex} />
      </div>

      {/* AI AGENTS — three small signal badges */}
      <div className="flex items-center gap-1 justify-start">
        <AgentBadge Icon={TrendingUp}    label="Tech" sig={techSig} conf={techConf} dim={noData} active={agentsActive} />
        <AgentBadge Icon={Globe}         label="Fund" sig={fundSig} conf={fundConf} dim={noData} active={agentsActive} />
        <AgentBadge Icon={MessageSquare} label="Sent" sig={sentSig} conf={sentConf} dim={noData} active={agentsActive} />
        <Arrow active={consensusActive} hex={finalHex} />
      </div>

      {/* CONSENSUS — score with bar */}
      <div className="flex items-center gap-2">
        <div
          className="flex flex-col items-center justify-center rounded-md px-2 py-1"
          style={{
            width: "100%",
            maxWidth: 110,
            height: 50,
            background: consensusActive ? `${finalHex}1f` : `${finalHex}10`,
            border: `1px solid ${finalHex}${consensusActive ? "66" : "33"}`,
          }}
        >
          <div className="flex items-center gap-1" style={{ color: finalHex }}>
            <GitMerge size={11} strokeWidth={2} />
            <span className="text-[10px] font-extrabold">
              {noData ? "—" : `${(consensus * 100).toFixed(0)}%`}
            </span>
          </div>
          <div className="w-full h-[3px] rounded mt-1.5" style={{ background: "rgba(255,255,255,0.08)" }}>
            <div
              className="h-full rounded transition-all"
              style={{
                width: `${Math.min(Math.abs(consensus) * 100, 100)}%`,
                background: finalHex,
                opacity: 0.7,
              }}
            />
          </div>
          <div className="text-[7px] mt-0.5" style={{ color: "rgba(255,255,255,0.4)" }}>
            CONF {noData ? "—" : `${(confidence * 100).toFixed(0)}%`}
          </div>
        </div>
        <Arrow active={riskActive} hex={finalHex} />
      </div>

      {/* RISK — verdict */}
      <div className="flex items-center gap-2">
        <div
          className="flex flex-col items-center justify-center rounded-md px-2 py-1"
          style={{
            width: "100%",
            maxWidth: 110,
            height: 50,
            background: riskActive ? `${verdictHex}1f` : `${verdictHex}10`,
            border: `1px solid ${verdictHex}${riskActive ? "66" : "33"}`,
          }}
        >
          <div className="flex items-center gap-1" style={{ color: verdictHex }}>
            <ShieldCheck size={11} strokeWidth={2} />
            <span className="text-[9px] font-extrabold uppercase tracking-wide">
              {noData ? "—" : verdict}
            </span>
          </div>
          <div className="text-[7px] mt-0.5" style={{ color: "rgba(255,255,255,0.4)" }}>
            POS · LEV · SL
          </div>
        </div>
        <Arrow active={decisionActive} hex={finalHex} />
      </div>

      {/* DECISION — final action */}
      <div className="flex items-center justify-end">
        <div
          className="flex flex-col items-center justify-center rounded-md px-3 py-1 min-w-[90px]"
          style={{
            height: 50,
            background: decisionActive ? `${finalHex}28` : `${finalHex}15`,
            border: `1px solid ${finalHex}${decisionActive ? "88" : "55"}`,
            boxShadow: decisionActive ? `0 0 18px ${finalHex}55` : `0 0 8px ${finalHex}22`,
          }}
        >
          <div style={{ color: finalHex, lineHeight: 0 }}>
            <Zap size={12} strokeWidth={2.5} />
          </div>
          <div className="text-[11px] font-extrabold mt-0.5" style={{ color: finalHex, letterSpacing: 1 }}>
            {finalAction}
          </div>
          {dec?.market_regime && (
            <div className="text-[6.5px] mt-0.5 uppercase tracking-wide" style={{ color: "rgba(255,255,255,0.35)" }}>
              {dec.market_regime.replace("_", " ")}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── main component ────────────────────────────────────────────────────────────
export function DecisionFlowMap() {
  const { data: decisions = [] } = useAgentDecisions(40)
  const { data: botStatus } = useBotStatus()
  const { data: tradingSymbolsData } = useTradingSymbols()

  // Pick latest decision per symbol from the polled window.
  const latestPerSymbol = React.useMemo(() => {
    const map = new Map<string, AgentDecisionLike>()
    for (const d of decisions as AgentDecisionLike[]) {
      const existing = map.get(d.symbol)
      if (!existing) { map.set(d.symbol, d); continue }
      const tNew = existing.timestamp ? new Date(existing.timestamp).getTime() : 0
      const tCur = d.timestamp ? new Date(d.timestamp).getTime() : 0
      if (tCur > tNew) map.set(d.symbol, d)
    }
    return Array.from(map.values()).sort((a, b) => a.symbol.localeCompare(b.symbol))
  }, [decisions])

  // Live in-flight symbol from bot progress
  const [currentStep, setCurrentStep] = React.useState<string | null>(null)
  const [activeSymbol, setActiveSymbol] = React.useState<string | null>(null)

  React.useEffect(() => {
    const step = botStatus?.current_step?.step
    const sym = botStatus?.current_step?.symbol
    if (step && step !== "idle") {
      setCurrentStep(step)
      if (sym) setActiveSymbol(sym)
    } else {
      setCurrentStep(null)
      setActiveSymbol(null)
    }
  }, [botStatus?.current_step])

  useWebSocket("bot_progress", (data: any) => {
    if (!data) return
    if (data.step === "idle") {
      setCurrentStep(null)
      setActiveSymbol(null)
    } else {
      setCurrentStep(data.step ?? null)
      if (data.symbol) setActiveSymbol(data.symbol)
    }
  })

  // Symbols to render: use ONLY user-enabled symbols from settings
  const symbolSet = React.useMemo(() => {
    const active = tradingSymbolsData?.active ?? []
    return [...active].sort()
  }, [tradingSymbolsData])

  const mostRecentTs = latestPerSymbol
    .map(d => (d.timestamp ? new Date(d.timestamp).getTime() : 0))
    .reduce((a, b) => Math.max(a, b), 0)

  return (
    <div className="w-full space-y-3">
      {/* header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-primary" />
          <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
            Decision Flow · Per Symbol
          </span>
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-60" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
          </span>
        </div>
        {mostRecentTs > 0 && (
          <span className="text-[9px] font-mono text-muted-foreground/60">
            last: {fmtDateTime(new Date(mostRecentTs).toISOString())}
          </span>
        )}
      </div>

      {/* canvas */}
      <div
        className="w-full rounded-2xl p-3 space-y-2"
        style={{ background: "var(--flow-bg)", border: "1px solid var(--flow-border)" }}
      >
        <style>{`
          @keyframes rowPulse {
            0%, 100% { border-color: rgba(251,191,36,0.25); }
            50%      { border-color: rgba(251,191,36,0.75); }
          }
        `}</style>

        {/* column header row */}
        <div
          className="grid items-center gap-2 px-3 pb-1"
          style={{ gridTemplateColumns: "92px 1fr 1fr 1fr 1fr 1fr" }}
        >
          {["SYMBOL", "DATA INPUTS", "AI AGENTS", "CONSENSUS", "RISK", "DECISION"].map(label => (
            <span
              key={label}
              className="text-[9px] font-bold uppercase tracking-[0.18em] text-muted-foreground/50"
            >
              {label}
            </span>
          ))}
        </div>

        {/* symbol rows */}
        {symbolSet.length === 0 ? (
          <div className="text-[10px] text-muted-foreground/50 text-center py-6">
            No decisions yet — bot will populate after the first analysis cycle.
          </div>
        ) : (
          symbolSet.map(sym => {
            const dec = latestPerSymbol.find(d => d.symbol === sym) ?? null
            return (
              <SymbolRow
                key={sym}
                symbol={sym}
                dec={dec}
                active={activeSymbol === sym}
                currentStep={currentStep}
              />
            )
          })
        )}
      </div>
    </div>
  )
}
