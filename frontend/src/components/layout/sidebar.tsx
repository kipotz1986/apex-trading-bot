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
  Zap,
  ShieldCheck
} from "lucide-react"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { ThemeToggle } from "./ThemeToggle"

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
    <aside className="w-20 lg:w-64 border-r border-white/[0.05] bg-background/60 backdrop-blur-3xl flex flex-col h-dvh sticky top-0 transition-all duration-300 group z-50">
      {/* Logo Section */}
      <div className="h-20 flex items-center px-6 gap-3">
        <div className="w-8 h-8 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(245,158,11,0.05)]">
          <Zap className="w-5 h-5 text-primary fill-primary/10" />
        </div>
        <span className="font-heading font-bold text-lg tracking-tight text-foreground hidden lg:block opacity-0 group-hover:opacity-100 lg:opacity-100 transition-opacity">
          APEX <span className="text-primary/90">TRADER</span>
        </span>
      </div>

      <Separator className="bg-white/[0.03] mx-4 w-auto" />

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
                      "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-300 group relative",
                      pathname === item.href 
                        ? "bg-primary/15 text-primary shadow-[inset_0_0_20px_rgba(16,185,129,0.05)]" 
                        : "text-white/60 hover:text-white/90 hover:bg-white/[0.03]"
                    )}
                  >
                    <item.icon className={cn(
                      "w-5 h-5 transition-transform duration-300 group-hover/item:scale-110",
                      pathname === item.href ? "text-primary opacity-100" : "opacity-50"
                    )} />
                    <span className="text-sm font-bold tracking-wide hidden lg:block opacity-0 group-hover:opacity-100 lg:opacity-100">
                      {item.label}
                    </span>
                    {pathname === item.href && (
                      <div className="absolute left-0 w-1 h-5 bg-primary rounded-r-full shadow-[0_0_10px_rgba(245,158,11,0.4)]" />
                    )}
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right" className="lg:hidden glass-card text-primary font-bold text-xs uppercase tracking-widest border-primary/30">
                  {item.label}
                </TooltipContent>
              </Tooltip>
            ))}
          </TooltipProvider>
        </nav>
      </ScrollArea>

      <Separator className="bg-white/[0.03] mx-4 w-auto" />

      {/* Bottom Section (Settings & Theme) */}
      <div className="p-4 space-y-2">
        <div className="flex items-center gap-2 lg:gap-3">
          <ThemeToggle />
          <Link
            href="/settings"
            className={cn(
              "flex-1 flex items-center gap-3 px-3 h-9 rounded-xl transition-all cursor-pointer",
              pathname === "/settings" 
                ? "bg-primary/15 text-primary" 
                : "text-white/40 hover:text-white/80 hover:bg-white/[0.03]"
            )}
          >
            <Settings className="w-4 h-4 shrink-0" />
            <span className="text-xs font-bold hidden lg:block uppercase tracking-wider">Settings</span>
          </Link>
        </div>
        
        <button 
          onClick={() => {
            localStorage.removeItem("token");
            window.location.href = "/login";
          }}
          className="w-full flex items-center gap-3 px-3 h-10 rounded-xl text-red-500/50 hover:text-red-400 hover:bg-red-500/10 transition-all cursor-pointer border border-transparent hover:border-red-500/10"
        >
          <Lock className="w-4 h-4 shrink-0" />
          <span className="text-xs font-bold hidden lg:block uppercase tracking-wider">Lock Session</span>
        </button>
      </div>

      {/* Status Footer */}
      <div className="p-6 hidden lg:block">
        <div className="p-4 rounded-2xl glass-card border-white/[0.03] group-hover:border-white/[0.08] transition-colors">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-1.5 h-1.5 rounded-full bg-primary/60 shadow-[0_0_8px_rgba(245,158,11,0.4)]" />
            <span className="text-[10px] font-bold text-primary/70 uppercase tracking-widest">Quantum Engine Active</span>
          </div>
          <div className="text-[10px] text-foreground/30 font-medium leading-relaxed">
            Multi-agent consensus stabilized. <br/>
            Neural latency: <span className="text-primary/60 font-bold">1.2ms</span>
          </div>
        </div>
      </div>
    </aside>
  )
}

