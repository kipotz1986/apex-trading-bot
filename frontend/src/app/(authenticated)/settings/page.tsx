"use client"

import React from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { 
  Settings as SettingsIcon, 
  ShieldCheck, 
  Bell, 
  Key, 
  Cpu, 
  LayoutDashboard 
} from "lucide-react"

export default function SettingsPage() {
  return (
    <div className="space-y-8 max-w-4xl animate-in fade-in duration-700">
      <div>
         <h1 className="text-3xl font-bold tracking-tight text-white">System Settings</h1>
         <p className="text-white/40 text-sm mt-1">Configure AI parameters, exchange API keys, and notification triggers.</p>
      </div>

      <div className="grid gap-8">
         {/* AI Configuration */}
         <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
            <CardHeader className="flex flex-row items-center gap-4">
               <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <Cpu className="w-5 h-5 text-emerald-500" />
               </div>
               <div>
                  <CardTitle className="text-lg text-white">AI Engine</CardTitle>
                  <CardDescription className="text-white/30">Select the primary model for consensus logic.</CardDescription>
               </div>
            </CardHeader>
            <CardContent className="space-y-6">
               <div className="grid gap-2">
                  <Label className="text-xs text-white/50 uppercase tracking-widest">Primary Model Provider</Label>
                  <Input defaultValue="OpenAI GPT-4o-mini" className="bg-white/5 border-white/10 text-white" />
               </div>
               <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/5">
                  <div className="space-y-1">
                     <p className="text-sm font-bold text-white">Advanced Reasoning</p>
                     <p className="text-[10px] text-white/30 uppercase tracking-widest">Use higher-cost models for complex regimes</p>
                  </div>
                  <Switch defaultChecked />
               </div>
            </CardContent>
         </Card>

         {/* Exchange Configuration */}
         <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
            <CardHeader className="flex flex-row items-center gap-4">
               <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
                  <Key className="w-5 h-5 text-blue-500" />
               </div>
               <div>
                  <CardTitle className="text-lg text-white">Exchange API</CardTitle>
                  <CardDescription className="text-white/30">Securely transmit orders to your exchange account.</CardDescription>
               </div>
            </CardHeader>
            <CardContent className="space-y-6">
               <div className="grid gap-6 md:grid-cols-2">
                  <div className="grid gap-2">
                     <Label className="text-xs text-white/50 uppercase tracking-widest">API Key</Label>
                     <Input value="••••••••••••••••" readOnly className="bg-white/5 border-white/10 text-white/50" />
                  </div>
                  <div className="grid gap-2">
                     <Label className="text-xs text-white/50 uppercase tracking-widest">API Secret</Label>
                     <Input type="password" value="••••••••••••••••" readOnly className="bg-white/5 border-white/10 text-white/50" />
                  </div>
               </div>
               <div className="flex justify-end pt-2">
                  <Button variant="outline" className="text-xs font-bold border-white/10 hover:bg-white/5">Update Credentials</Button>
               </div>
            </CardContent>
         </Card>

         {/* Risk Management */}
         <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
            <CardHeader className="flex flex-row items-center gap-4">
               <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                  <ShieldCheck className="w-5 h-5 text-red-500" />
               </div>
               <div>
                  <CardTitle className="text-lg text-white">Risk Parameters</CardTitle>
                  <CardDescription className="text-white/30">Hardcoded safety limits and circuit breakers.</CardDescription>
               </div>
            </CardHeader>
            <CardContent className="space-y-6">
               <div className="grid md:grid-cols-3 gap-6">
                  <div className="space-y-2">
                     <Label className="text-[10px] text-white/50 uppercase tracking-widest">Daily Loss Limit</Label>
                     <p className="text-xl font-bold text-white">3.0%</p>
                  </div>
                  <div className="space-y-2">
                     <Label className="text-[10px] text-white/50 uppercase tracking-widest">Max Leverage</Label>
                     <p className="text-xl font-bold text-white">10x</p>
                  </div>
                  <div className="space-y-2">
                     <Label className="text-[10px] text-white/50 uppercase tracking-widest">Max Position Size</Label>
                     <p className="text-xl font-bold text-white">15.0%</p>
                  </div>
               </div>
            </CardContent>
         </Card>
      </div>

      <div className="flex justify-end gap-3 pb-12">
         <Button variant="ghost" className="text-white/40 hover:text-white">Discard Changes</Button>
         <Button className="bg-emerald-500 hover:bg-emerald-400 text-black font-bold shadow-[0_0_20px_rgba(16,185,129,0.2)]">
            Save System Configuration
         </Button>
      </div>
    </div>
  )
}
