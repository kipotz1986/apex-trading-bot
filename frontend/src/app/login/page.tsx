"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ShieldAlert, Zap, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { api } from "@/lib/api"

export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState("admin")
  const [password, setPassword] = useState("")
  const [totpCode, setTotpCode] = useState("")
  
  const [step, setStep] = useState<1 | 2>(1)
  const [tempToken, setTempToken] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      const formData = new FormData()
      formData.append("username", username)
      formData.append("password", password)

      const { data } = await api.post("/auth/login", formData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
      })

      if (data.requires_2fa) {
        setTempToken(data.temp_token)
        setStep(2)
        toast.success("Credentials accepted", { description: "Please enter your 2FA code." })
      }
    } catch (err: any) {
      toast.error("Login Failed", {
        description: err.response?.data?.detail || "Invalid credentials."
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerify2FA = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      const { data } = await api.post("/auth/verify-2fa", {
        totp_code: totpCode,
        temp_token: tempToken
      })

      if (data.access_token) {
        localStorage.setItem("token", data.access_token)
        toast.success("Authentication Successful")
        router.push("/dashboard")
      }
    } catch (err: any) {
      toast.error("2FA Failed", {
        description: err.response?.data?.detail || "Invalid code."
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#020504] flex items-center justify-center p-4">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-emerald-500/10 blur-[120px] rounded-full" />
      </div>

      <Card className="w-full max-w-md bg-[#050B0A]/80 border-white/10 backdrop-blur-xl shadow-2xl relative z-10 overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 via-emerald-400 to-blue-500" />
        
        <CardHeader className="space-y-3 pb-6 text-center">
          <div className="mx-auto w-12 h-12 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl flex items-center justify-center mb-2 shadow-[0_0_20px_rgba(16,185,129,0.2)]">
            {step === 1 ? <Zap className="w-6 h-6 text-emerald-500" /> : <ShieldAlert className="w-6 h-6 text-emerald-500" />}
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight text-white">APEX System</CardTitle>
          <CardDescription className="text-white/40 uppercase tracking-widest text-[10px] font-bold">
            {step === 1 ? "Secure Authentication Required" : "Two-Factor Verification"}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {step === 1 ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username" className="text-xs font-bold text-white/70 uppercase tracking-wider">Username</Label>
                <Input 
                  id="username" 
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={isLoading}
                  className="bg-white/5 border-white/10 text-white placeholder:text-white/20 h-12 focus-visible:ring-emerald-500/50"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-xs font-bold text-white/70 uppercase tracking-wider">Password</Label>
                <Input 
                  id="password" 
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  className="bg-white/5 border-white/10 text-white placeholder:text-white/20 h-12 focus-visible:ring-emerald-500/50"
                  placeholder="••••••••"
                />
              </div>
              <Button 
                type="submit" 
                disabled={isLoading}
                className="w-full h-12 bg-emerald-500 hover:bg-emerald-400 text-black font-bold uppercase tracking-widest text-xs mt-2"
              >
                {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Authenticate"}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleVerify2FA} className="space-y-4">
              <div className="space-y-2 text-center mb-6">
                <p className="text-xs text-white/60">Enter the 6-digit code from your authenticator app.</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="totp" className="text-xs font-bold text-white/70 uppercase tracking-wider">Authenticator Code</Label>
                <Input 
                  id="totp" 
                  autoFocus
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/[^0-9]/g, ''))}
                  disabled={isLoading}
                  className="bg-white/5 border-white/10 text-white text-center text-2xl tracking-[0.5em] font-mono h-14 focus-visible:ring-emerald-500/50"
                  placeholder="000000"
                />
              </div>
              <Button 
                type="submit" 
                disabled={isLoading || totpCode.length !== 6}
                className="w-full h-12 bg-emerald-500 hover:bg-emerald-400 text-black font-bold uppercase tracking-widest text-xs mt-2"
              >
                {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Verify Access"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
