"use client"

import React, { useState } from "react"
import { useRouter } from "next/navigation"
import { Lock, Mail, ChevronRight } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"

export default function LoginPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState(1) // 1: Credentials, 2: 2FA

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    
    // Simulasi transisi ke 2FA
    if (step === 1) {
      setTimeout(() => {
        setStep(2)
        setLoading(false)
      }, 1000)
    } else {
      // 2FA submission logic here
      setTimeout(() => {
        router.push("/dashboard")
      }, 1000)
    }
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#050B0A] px-4 relative overflow-hidden">
      {/* Background Chart Overlay (Blured) */}
      <div className="absolute inset-0 opacity-10 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/20 blur-[120px] rounded-full" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-emerald-500/10 blur-[120px] rounded-full" />
      </div>

      <Card className="w-full max-w-md bg-black/40 border-emerald-500/20 backdrop-blur-xl shadow-2xl relative z-10 overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-emerald-500 to-transparent opacity-50" />
        
        <CardHeader className="text-center pb-8 pt-10">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.1)]">
                <span className="text-emerald-500 text-3xl font-bold italic tracking-tighter">AI</span>
            </div>
          </div>
          <CardTitle className="text-3xl font-bold tracking-tight text-white mb-2">ASTRATECH</CardTitle>
          <CardDescription className="text-emerald-500/60 font-medium tracking-wide uppercase text-xs">
            {step === 1 ? "Sign in to your dashboard" : "Two-factor authentication"}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {step === 1 ? (
              <>
                <div className="space-y-2">
                  <Label className="text-emerald-500/70 text-xs font-semibold ml-1 uppercase tracking-wider">Email Address</Label>
                  <div className="relative group">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-emerald-500/40 group-focus-within:text-emerald-500 transition-colors" />
                    <Input 
                      type="email" 
                      placeholder="Enter your email" 
                      className="bg-black/40 border-white/5 pl-10 h-12 focus-visible:ring-emerald-500/50 focus-visible:border-emerald-500/50 text-white placeholder:text-white/20 transition-all"
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label className="text-emerald-500/70 text-xs font-semibold ml-1 uppercase tracking-wider">Password</Label>
                  <div className="relative group">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-emerald-500/40 group-focus-within:text-emerald-500 transition-colors" />
                    <Input 
                      type="password" 
                      placeholder="Enter your password" 
                      className="bg-black/40 border-white/5 pl-10 h-12 focus-visible:ring-emerald-500/50 focus-visible:border-emerald-500/50 text-white placeholder:text-white/20 transition-all"
                      required
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] font-bold text-emerald-500/50 tracking-tighter px-1 pb-2">
                   <button type="button" className="hover:text-emerald-400 transition-colors">FORGOT PASSWORD?</button>
                </div>
              </>
            ) : (
              <div className="space-y-4 text-center">
                <Label className="text-emerald-500/70 text-xs font-semibold uppercase tracking-wider mb-4 block">Enter 6-digit code</Label>
                <div className="flex justify-between gap-2 px-1">
                  {[1, 2, 3, 4, 5, 6].map((i) => (
                    <Input 
                      key={i} 
                      type="text" 
                      maxLength={1} 
                      className="w-12 h-14 bg-black/40 border-emerald-500/20 text-center text-xl font-bold text-emerald-400 focus-visible:ring-emerald-500/50 rounded-lg shadow-[0_0_10px_rgba(16,185,129,0.1)]"
                      required
                    />
                  ))}
                </div>
                <p className="text-[10px] text-white/30 mt-4 leading-relaxed tracking-tight">
                  Please enter the code generated in your Authenticator app to secure your account.
                </p>
              </div>
            )}

            <Button 
              type="submit" 
              className="w-full h-14 bg-emerald-500 hover:bg-emerald-400 text-black font-bold text-base rounded-xl transition-all shadow-[0_0_25px_rgba(16,185,129,0.3)] hover:scale-[1.02] active:scale-[0.98]"
              disabled={loading}
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
              ) : (
                <div className="flex items-center gap-2">
                  <span>{step === 1 ? "SIGN IN" : "VERIFY CODE"}</span>
                  <ChevronRight className="w-4 h-4" />
                </div>
              )}
            </Button>
          </form>
          
          <div className="mt-8 text-center">
             <p className="text-[10px] font-bold text-emerald-500/30 uppercase tracking-widest flex items-center justify-center gap-2">
                Secure Institutional Access <Lock className="w-2.5 h-2.5" />
             </p>
          </div>
        </CardContent>
      </Card>
      
      {/* Footer Decoration */}
      <div className="absolute bottom-10 text-[9px] text-white/10 font-mono tracking-widest uppercase flex gap-8">
         <span>Latency: 1.2ms</span>
         <span>Hash: 0x...F3E2</span>
         <span>Relay: SINGAPORE-01</span>
      </div>
    </div>
  )
}
