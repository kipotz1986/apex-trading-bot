"use client"

import React from "react"
import { Sidebar } from "@/components/layout/sidebar"
import { Bell, Search, User, Globe, ChevronDown } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuLabel, 
  DropdownMenuSeparator, 
  DropdownMenuTrigger 
} from "@/components/ui/dropdown-menu"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-dvh bg-background text-foreground selection:bg-emerald-500/30">
      <Sidebar />
      
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navigation */}
        <header className="h-20 border-b border-emerald-500/10 bg-popover/80 backdrop-blur-md sticky top-0 z-30 flex items-center justify-between px-8">
          <div className="flex items-center gap-8 flex-1 max-w-xl">
            <div className="relative group flex-1 hidden md:block">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/80 group-focus-within:text-primary transition-colors" />
              <Input 
                className="bg-muted/50 border-border/50 pl-10 focus-visible:ring-primary/50 focus-visible:border-primary/50 text-xs font-medium" 
                placeholder="Search metrics, trades, or logs..."
              />
            </div>
          </div>

          <div className="flex items-center gap-6">
            {/* Status Indicators */}
            <div className="hidden lg:flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 shadow-[0_0_10px_rgba(16,185,129,0.05)]">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] font-bold text-primary uppercase tracking-widest">Global Status: Online</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20">
                <Globe className="w-3 h-3 text-amber-500" />
                <span className="text-[10px] font-bold text-amber-500 uppercase tracking-widest">Network: BYBIT_MAINNET</span>
              </div>
            </div>

            <Separator orientation="vertical" className="h-6 bg-muted/50 hidden md:block" />

            {/* Actions */}
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-primary hover:bg-emerald-500/5 relative">
                <Bell className="w-5 h-5" />
                <div className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-popover" />
              </Button>
              
              <DropdownMenu>
                <DropdownMenuTrigger>
                  <Button variant="ghost" className="h-12 pl-1 pr-3 rounded-full hover:bg-muted/50 flex items-center gap-3 transition-all">
                    <Avatar className="h-8 w-8 border border-primary/20 shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                      <AvatarImage src="https://github.com/shadcn.png" />
                      <AvatarFallback className="bg-emerald-500/20 text-primary text-xs font-bold">MT</AvatarFallback>
                    </Avatar>
                    <div className="text-left hidden sm:block">
                      <p className="text-xs font-bold text-foreground tracking-tight">Mohamad Taufiq</p>
                      <p className="text-[10px] font-medium text-primary/60 uppercase tracking-tighter">Owner Account</p>
                    </div>
                    <ChevronDown className="w-3 h-3 text-muted-foreground/60" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="bg-popover border-primary/20 text-foreground min-w-[200px] mt-2 backdrop-blur-xl shadow-2xl">
                  <DropdownMenuLabel className="text-[10px] font-bold text-primary/50 uppercase tracking-widest px-4 pt-3">Account Security</DropdownMenuLabel>
                  <DropdownMenuItem className="focus:bg-primary/10 focus:text-primary cursor-pointer px-4 py-3">
                    <User className="w-4 h-4 mr-3" /> Profile Settings
                  </DropdownMenuItem>
                  <DropdownMenuSeparator className="bg-muted/50" />
                  <DropdownMenuItem className="focus:bg-red-500/10 focus:text-red-400 cursor-pointer px-4 py-3 text-red-500/80 font-semibold">
                    Logout Console
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 relative overflow-hidden bg-background/50">
          {/* Dashboard Decorations - Refined Mesh Gradient */}
          <div className="absolute top-[-10%] right-[-10%] w-[70%] h-[70%] bg-emerald-500/[0.03] blur-[120px] -z-10 rounded-full animate-pulse" />
          <div className="absolute bottom-[-10%] left-[-10%] w-[70%] h-[70%] bg-blue-500/[0.03] blur-[120px] -z-10 rounded-full" />
          <div className="absolute top-[20%] left-[20%] w-[30%] h-[30%] bg-purple-500/[0.02] blur-[100px] -z-10 rounded-full" />
          
          <ScrollArea className="h-[calc(100vh-80px)]">
            <div className="p-8 pb-12">
              {children}
            </div>
          </ScrollArea>
        </main>
      </div>
    </div>
  )
}
