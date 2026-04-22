"use client"

import React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { 
  LayoutDashboard, 
  TrendingUp, 
  Bot, 
  Brain, 
  History, 
  Activity,
  Settings, 
  Lock,
  Zap
} from "lucide-react"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

const menuItems = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/dashboard" },
  { icon: TrendingUp, label: "Trading", href: "/trading" },
  { icon: Bot, label: "AI Agents", href: "/agents" },
  { icon: Brain, label: "Self-Learning", href: "/learning" },
  { icon: History, label: "Backtest", href: "/backtest" },
  { icon: Activity, label: "System Logs", href: "/logs" },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-20 lg:w-64 border-r border-emerald-500/10 bg-[#050B0A] flex flex-col h-screen sticky top-0 transition-all duration-300 group">
      {/* Logo Section */}
      <div className="h-20 flex items-center px-6 gap-3">
        <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(16,185,129,0.1)]">
          <Zap className="w-5 h-5 text-emerald-500 fill-emerald-500/20" />
        </div>
        <span className="font-bold text-lg tracking-tight text-white hidden lg:block opacity-0 group-hover:opacity-100 lg:opacity-100 transition-opacity">
          APEX <span className="text-emerald-500">TRADER</span>
        </span>
      </div>

      <Separator className="bg-emerald-500/5 mx-4 w-auto" />

      {/* Navigation Section */}
      <ScrollArea className="flex-1 px-4 py-6">
        <nav className="space-y-2">
          <TooltipProvider delay={0}>
            {menuItems.map((item) => (
              <Tooltip key={item.href}>
                <TooltipTrigger>
                  <Link
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 px-3 h-12 rounded-xl transition-all duration-200 relative group/item",
                      pathname === item.href 
                        ? "bg-emerald-500/10 text-emerald-500 shadow-[inset_0_0_10px_rgba(16,185,129,0.05)]" 
                        : "text-white/40 hover:text-white hover:bg-white/5"
                    )}
                  >
                    <item.icon className={cn(
                      "w-5 h-5 transition-transform duration-300 group-hover/item:scale-110",
                      pathname === item.href ? "text-emerald-500 drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]" : ""
                    )} />
                    <span className="text-sm font-semibold tracking-wide hidden lg:block opacity-0 group-hover:opacity-100 lg:opacity-100">
                      {item.label}
                    </span>
                    {pathname === item.href && (
                      <div className="absolute left-0 w-1 h-6 bg-emerald-500 rounded-r-full shadow-[0_0_10px_rgba(16,185,129,0.8)]" />
                    )}
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right" className="lg:hidden bg-emerald-950 border-emerald-500/30 text-emerald-400 font-bold text-xs uppercase tracking-widest">
                  {item.label}
                </TooltipContent>
              </Tooltip>
            ))}
          </TooltipProvider>
        </nav>
      </ScrollArea>

      <Separator className="bg-emerald-500/5 mx-4 w-auto" />

      {/* Bottom Section (Settings & Lock) */}
      <div className="p-4 space-y-2">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 px-3 h-12 rounded-xl text-white/40 hover:text-white hover:bg-white/5 transition-all",
            pathname === "/settings" && "bg-emerald-500/10 text-emerald-500"
          )}
        >
          <Settings className="w-5 h-5 shrink-0" />
          <span className="text-sm font-semibold hidden lg:block">Settings</span>
        </Link>
        <button 
          onClick={() => {
            localStorage.removeItem("token");
            window.location.href = "/login";
          }}
          className="w-full flex items-center gap-3 px-3 h-12 rounded-xl text-red-500/50 hover:text-red-400 hover:bg-red-500/5 transition-all"
        >
          <Lock className="w-5 h-5 shrink-0" />
          <span className="text-sm font-semibold hidden lg:block">Lock Console</span>
        </button>
      </div>

      {/* Status Footer */}
      <div className="p-6 hidden lg:block">
        <div className="p-4 rounded-2xl bg-emerald-500/5 border border-emerald-500/10">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-widest">System Live</span>
          </div>
          <div className="text-[10px] text-white/30 font-medium leading-relaxed">
            Market synchronization active. Latency: 4ms
          </div>
        </div>
      </div>
    </aside>
  )
}
