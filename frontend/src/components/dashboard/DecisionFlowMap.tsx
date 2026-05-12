"use client"

import React from "react"
import {
  BarChart2, Newspaper, Radio,
  TrendingUp, Globe, MessageSquare,
  GitMerge, ShieldCheck, Zap,
  Brain,
} from "lucide-react"
import { useAgentDecisions } from "@/hooks/useApi"
import { fmtDateTime } from "@/lib/dateFormat"

// ─── helpers ──────────────────────────────────────────────────────────────────
function getSig(obj: any): string {
  if (!obj) return "NEUTRAL"
  return typeof obj === "string" ? obj : (obj?.signal ?? "NEUTRAL")
}

function sigHex(sig: string): string {
  const s = sig.toUpperCase()
  if (s.includes("BUY") || s.includes("LONG"))  return "#10b981"
  if (s.includes("SELL") || s.includes("SHORT")) return "#ef4444"
  return "#f59e0b"
}

function sigLabel(sig: string): string {
  const s = sig.toUpperCase()
  if (s.includes("STRONG_BUY"))  return "STRONG BUY"
  if (s.includes("BUY") || s.includes("LONG"))   return "BUY"
  if (s.includes("STRONG_SELL")) return "STRONG SELL"
  if (s.includes("SELL") || s.includes("SHORT")) return "SELL"
  return "NEUTRAL"
}

function actionLabel(action: string): string {
  if (action.includes("LONG"))  return "LONG"
  if (action.includes("SHORT")) return "SHORT"
  return "HOLD"
}

// ─── SVG layout constants (viewBox 0 0 1060 540) ──────────────────────────────
const VW = 1060
const VH = 540
const NW = 138   // node width
const NH = 80    // node height

// center (x, y) of every node
const C: Record<string, { x: number; y: number }> = {
  price:       { x: 90,  y: 110 },
  news:        { x: 90,  y: 270 },
  social:      { x: 90,  y: 430 },
  technical:   { x: 308, y: 110 },
  fundamental: { x: 308, y: 270 },
  sentiment:   { x: 308, y: 430 },
  consensus:   { x: 572, y: 270 },
  risk:        { x: 778, y: 270 },
  output:      { x: 966, y: 270 },
}

const re = (id: string) => ({ x: C[id].x + NW / 2, y: C[id].y })
const le = (id: string) => ({ x: C[id].x - NW / 2, y: C[id].y })

function bezier(f: { x: number; y: number }, t: { x: number; y: number }) {
  const dx = Math.abs(t.x - f.x) * 0.45
  return `M ${f.x} ${f.y} C ${f.x + dx} ${f.y} ${t.x - dx} ${t.y} ${t.x} ${t.y}`
}

// connections and which signal drives each edge
const EDGES = [
  { id: "p-t",  from: "price",      to: "technical",   sigKey: "technical"   },
  { id: "n-f",  from: "news",       to: "fundamental", sigKey: "fundamental" },
  { id: "s-s",  from: "social",     to: "sentiment",   sigKey: "sentiment"   },
  { id: "t-c",  from: "technical",  to: "consensus",   sigKey: "technical"   },
  { id: "f-c",  from: "fundamental",to: "consensus",   sigKey: "fundamental" },
  { id: "s-c",  from: "sentiment",  to: "consensus",   sigKey: "sentiment"   },
  { id: "c-r",  from: "consensus",  to: "risk",        sigKey: "consensus"   },
  { id: "r-o",  from: "risk",       to: "output",      sigKey: "output"      },
]

// ─── single node rendered as <foreignObject> ───────────────────────────────────
interface NodeProps {
  id: string
  label: string
  sublabel?: string
  apiSources?: string[]   // list of 3rd-party APIs shown as pills
  nodeH?: number          // override height (input nodes are taller)
  Icon: React.ComponentType<{ size?: number; strokeWidth?: number }>
  hex: string
  badge?: string
  animKey: number
  dim?: boolean
}

function FlowNode({ id, label, sublabel, apiSources, nodeH, Icon, hex, badge, animKey, dim }: NodeProps) {
  const cx = C[id].x
  const cy = C[id].y
  const h = nodeH ?? NH
  return (
    <foreignObject
      key={animKey}
      x={cx - NW / 2}
      y={cy - h / 2}
      width={NW}
      height={h}
      style={{ overflow: "visible" }}
    >
      <div
        // @ts-ignore – xmlns required for foreignObject HTML root
        xmlns="http://www.w3.org/1999/xhtml"
        style={{
          width: NW,
          height: h,
          background: dim ? "rgba(255,255,255,0.01)" : `${hex}0d`,
          border: `1px solid ${hex}${dim ? "18" : "35"}`,
          borderRadius: 14,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 3,
          padding: "8px 6px",
          boxSizing: "border-box",
          animation: `nodeFlash 0.8s ease-out`,
          boxShadow: dim ? "none" : `0 0 18px ${hex}20`,
        }}
      >
        <div style={{ color: dim ? "rgba(255,255,255,0.2)" : hex, lineHeight: 0 }}>
          <Icon size={16} strokeWidth={2} />
        </div>
        <span style={{
          fontSize: 8, fontWeight: 800, letterSpacing: "0.1em",
          color: dim ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.55)",
          textTransform: "uppercase", textAlign: "center", lineHeight: 1.3,
        }}>
          {label}
        </span>
        {sublabel && (
          <span style={{ fontSize: 7, color: "rgba(255,255,255,0.2)", textAlign: "center" }}>
            {sublabel}
          </span>
        )}
        {badge && (
          <span style={{
            fontSize: 8, fontWeight: 900,
            color: hex,
            background: `${hex}18`,
            borderRadius: 4, padding: "1px 6px",
            textTransform: "uppercase", letterSpacing: "0.05em",
          }}>
            {badge}
          </span>
        )}
        {apiSources && apiSources.length > 0 && (
          <div style={{
            display: "flex", flexWrap: "wrap", gap: 3,
            justifyContent: "center", marginTop: 2,
          }}>
            {apiSources.map(src => (
              <span key={src} style={{
                fontSize: 6.5, fontWeight: 800,
                letterSpacing: "0.04em",
                color: dim ? "rgba(99,102,241,0.25)" : "rgba(129,140,248,0.9)",
                background: dim ? "rgba(99,102,241,0.04)" : "rgba(99,102,241,0.12)",
                border: `1px solid ${dim ? "rgba(99,102,241,0.1)" : "rgba(99,102,241,0.28)"}`,
                borderRadius: 3, padding: "1px 5px",
              }}>
                {src}
              </span>
            ))}
          </div>
        )}
      </div>
    </foreignObject>
  )
}

// ─── main component ────────────────────────────────────────────────────────────
export function DecisionFlowMap() {
  const { data: decisions = [] } = useAgentDecisions(1)
  const dec = decisions[0] ?? null

  const [animKey, setAnimKey] = React.useState(0)
  const prevId = React.useRef<number | null>(null)

  React.useEffect(() => {
    if (!dec) return
    if (dec.id !== prevId.current) {
      prevId.current = dec.id
      setAnimKey(k => k + 1)
    }
  }, [dec?.id])

  // extract signals
  const sigs: Record<string, string> = {}
  if (dec?.agent_signals) {
    for (const [k, v] of Object.entries(dec.agent_signals)) {
      sigs[k] = getSig(v)
    }
  }

  const techSig  = sigs.technical   ?? "NEUTRAL"
  const fundSig  = sigs.fundamental ?? "NEUTRAL"
  const sentSig  = sigs.sentiment   ?? "NEUTRAL"
  const action   = dec?.action ?? "HOLD"
  const consensus = dec?.consensus_score ?? 0
  const conHex   = sigHex(action)

  // edge color resolver
  function edgeHex(sigKey: string) {
    if (sigKey === "technical")   return sigHex(techSig)
    if (sigKey === "fundamental") return sigHex(fundSig)
    if (sigKey === "sentiment")   return sigHex(sentSig)
    if (sigKey === "consensus")   return conHex
    if (sigKey === "output")      return conHex
    return "#374151"
  }

  const noData = !dec

  return (
    <div className="w-full space-y-3">
      {/* header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-emerald-500" />
          <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">
            Decision Flow
          </span>
          {/* live pulse */}
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-60" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
          </span>
        </div>
        {dec && (
          <span className="text-[9px] font-mono text-white/20">
            {fmtDateTime(dec.timestamp)} · {dec.symbol}
          </span>
        )}
      </div>

      {/* SVG canvas */}
      <div className="w-full rounded-2xl overflow-hidden" style={{ background: "rgba(255,255,255,0.01)", border: "1px solid rgba(255,255,255,0.05)" }}>
        <svg
          viewBox={`0 0 ${VW} ${VH}`}
          className="w-full"
          style={{ display: "block" }}
        >
          <defs>
            {/* arrow marker */}
            {["emerald", "red", "amber", "gray"].map((name) => {
              const color = name === "emerald" ? "#10b981" : name === "red" ? "#ef4444" : name === "amber" ? "#f59e0b" : "#374151"
              return (
                <marker
                  key={name}
                  id={`arrow-${name}`}
                  markerWidth="7" markerHeight="7"
                  refX="6" refY="3.5"
                  orient="auto"
                >
                  <polygon points="0 0, 7 3.5, 0 7" fill={color} opacity="0.7" />
                </marker>
              )
            })}

            {/* keyframe animations */}
            <style>{`
              @keyframes flowDash {
                from { stroke-dashoffset: 40; }
                to   { stroke-dashoffset: 0; }
              }
              @keyframes nodeFlash {
                0%   { opacity: 0.4; transform: scale(0.96); }
                30%  { opacity: 1;   transform: scale(1.03); }
                100% { opacity: 1;   transform: scale(1); }
              }
              @keyframes flowBurst {
                0%   { stroke-dashoffset: 80; opacity: 0; }
                20%  { opacity: 1; }
                100% { stroke-dashoffset: 0; opacity: 1; }
              }
            `}</style>
          </defs>

          {/* ── section labels ── */}
          {[
            { x: 90,  label: "DATA INPUTS" },
            { x: 308, label: "AI AGENTS" },
            { x: 572, label: "CONSENSUS" },
            { x: 778, label: "RISK" },
            { x: 966, label: "DECISION" },
          ].map(({ x, label }) => (
            <text
              key={label}
              x={x} y={28}
              textAnchor="middle"
              fontSize={9}
              fontWeight={700}
              letterSpacing={1.5}
              fill="rgba(255,255,255,0.15)"
              style={{ textTransform: "uppercase" }}
            >
              {label}
            </text>
          ))}

          {/* ── separator lines ── */}
          {[208, 440, 670, 870].map(xPos => (
            <line
              key={xPos}
              x1={xPos} y1={40} x2={xPos} y2={VH - 20}
              stroke="rgba(255,255,255,0.04)" strokeWidth={1}
              strokeDasharray="4 4"
            />
          ))}

          {/* ── edges ── */}
          {EDGES.map(({ id, from, to, sigKey }) => {
            const hex = noData ? "#1f2937" : edgeHex(sigKey)
            const markerName = noData ? "gray"
              : hex === "#10b981" ? "emerald"
              : hex === "#ef4444" ? "red"
              : hex === "#f59e0b" ? "amber"
              : "gray"
            return (
              <path
                key={id}
                d={bezier(re(from), le(to))}
                fill="none"
                stroke={hex}
                strokeWidth={1.8}
                strokeOpacity={noData ? 0.15 : 0.55}
                strokeDasharray="8 5"
                markerEnd={`url(#arrow-${markerName})`}
                style={{
                  animation: `flowDash ${noData ? 3 : 1.4}s linear infinite`,
                }}
              />
            )
          })}

          {/* ── nodes ── */}

          {/* INPUT nodes — show actual 3rd-party data sources */}
          <FlowNode
            key={`price-${animKey}`} id="price" label="Market Prices"
            sublabel="OHLCV · Funding · OI · Order Book"
            apiSources={["Bybit WS", "CCXT REST"]}
            nodeH={100}
            Icon={BarChart2} hex="#6366f1" animKey={animKey} dim={noData}
          />
          <FlowNode
            key={`news-${animKey}`} id="news" label="News & Events"
            sublabel="Headlines · Macro · Per-Coin News"
            apiSources={["CryptoCompare", "CoinGecko"]}
            nodeH={100}
            Icon={Newspaper} hex="#6366f1" animKey={animKey} dim={noData}
          />
          <FlowNode
            key={`social-${animKey}`} id="social" label="Social Signals"
            sublabel="Fear & Greed · Whale Transfers · Gas"
            apiSources={["Alternative.me", "Etherscan", "Blockchain.com", "Solana RPC"]}
            nodeH={100}
            Icon={Radio} hex="#6366f1" animKey={animKey} dim={noData}
          />

          {/* AGENT nodes */}
          <FlowNode key={`tech-${animKey}`}   id="technical"   label="Technical"      Icon={TrendingUp}   hex={noData ? "#374151" : sigHex(techSig)} badge={noData ? undefined : sigLabel(techSig)} animKey={animKey} dim={noData} />
          <FlowNode key={`fund-${animKey}`}   id="fundamental" label="Fundamental"    Icon={Globe}        hex={noData ? "#374151" : sigHex(fundSig)} badge={noData ? undefined : sigLabel(fundSig)} animKey={animKey} dim={noData} />
          <FlowNode key={`sent-${animKey}`}   id="sentiment"   label="Sentiment"      Icon={MessageSquare} hex={noData ? "#374151" : sigHex(sentSig)} badge={noData ? undefined : sigLabel(sentSig)} animKey={animKey} dim={noData} />

          {/* CONSENSUS */}
          <FlowNode
            key={`cons-${animKey}`}
            id="consensus"
            label="Consensus Engine"
            Icon={GitMerge}
            hex={noData ? "#374151" : conHex}
            badge={noData ? undefined : `${(consensus * 100).toFixed(0)}%`}
            animKey={animKey}
            dim={noData}
          />

          {/* RISK */}
          <FlowNode
            key={`risk-${animKey}`}
            id="risk"
            label="Risk Manager"
            sublabel="Position · Leverage · SL"
            Icon={ShieldCheck}
            hex={noData ? "#374151" : conHex}
            animKey={animKey}
            dim={noData}
          />

          {/* OUTPUT */}
          <FlowNode
            key={`out-${animKey}`}
            id="output"
            label="Final Action"
            Icon={Zap}
            hex={noData ? "#374151" : conHex}
            badge={noData ? "—" : actionLabel(action)}
            animKey={animKey}
            dim={noData}
          />

          {/* ── confidence bar under consensus node ── */}
          {!noData && (() => {
            const bx = C.consensus.x - 46
            const by = C.consensus.y + NH / 2 + 10
            const bw = 92
            const bh = 5
            return (
              <>
                <rect x={bx} y={by} width={bw} height={bh} rx={3} fill="rgba(255,255,255,0.06)" />
                <rect x={bx} y={by} width={bw * Math.min(consensus, 1)} height={bh} rx={3} fill={conHex} opacity={0.7} />
                <text x={C.consensus.x} y={by + 16} textAnchor="middle" fontSize={8} fill="rgba(255,255,255,0.25)" fontWeight={600}>
                  CONFIDENCE
                </text>
              </>
            )
          })()}

          {/* ── market regime badge ── */}
          {dec?.market_regime && (
            <g>
              <rect
                x={VW / 2 - 52} y={VH - 34}
                width={104} height={20} rx={5}
                fill="rgba(255,255,255,0.03)"
                stroke="rgba(255,255,255,0.08)"
                strokeWidth={1}
              />
              <text
                x={VW / 2} y={VH - 20}
                textAnchor="middle"
                fontSize={8}
                fontWeight={700}
                fill="rgba(255,255,255,0.3)"
                letterSpacing={1}
              >
                {dec.market_regime.toUpperCase().replace("_", " ")} REGIME
              </text>
            </g>
          )}
        </svg>
      </div>
    </div>
  )
}
