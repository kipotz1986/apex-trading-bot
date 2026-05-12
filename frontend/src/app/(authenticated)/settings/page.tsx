"use client"

import React, { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import {
  Cpu,
  Key,
  History,
  AlertTriangle,
  Bell,
  Shield,
  Scale,
  Zap,
  Flame,
  Skull,
  Sliders,
  Check,
  Coins
} from "lucide-react"
import {
  useSystemSettings,
  useUpdateAISettings,
  useExchangeProfiles,
  useUpdateExchangeProfile,
  useTestExchangeConnection,
  useAuditLogs,
  useAIModels,
  useUpdateNotificationSettings,
  useTestTelegram,
  useModeProfiles,
  useSetModeProfile,
  useTradingSymbols,
  useUpdateTradingSymbols,
  type ModeProfile
} from "@/hooks/useApi"

const MODE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  Shield, Scale, Zap, Flame, Skull,
}

const MODE_COLORS: Record<string, { bg: string; border: string; text: string; ring: string }> = {
  emerald: { bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400", ring: "ring-emerald-500/50" },
  blue: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400", ring: "ring-blue-500/50" },
  amber: { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400", ring: "ring-amber-500/50" },
  orange: { bg: "bg-orange-500/10", border: "border-orange-500/30", text: "text-orange-400", ring: "ring-orange-500/50" },
  red: { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400", ring: "ring-red-500/50" },
}
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"

export default function SettingsPage() {
  const { data: initialSettings, isLoading, error } = useSystemSettings()
  const { data: profiles } = useExchangeProfiles()
  const { data: auditLogs } = useAuditLogs()
  
  const updateAI = useUpdateAISettings()
  const updateProfile = useUpdateExchangeProfile()
  const testConn = useTestExchangeConnection()
  const updateNotifications = useUpdateNotificationSettings()
  const testTelegram = useTestTelegram()
  const { data: modeData } = useModeProfiles()
  const setMode = useSetModeProfile()
  const { data: symbolData } = useTradingSymbols()
  const updateSymbols = useUpdateTradingSymbols()

  const handleToggleSymbol = async (symbol: string) => {
    if (!symbolData) return
    const isActive = symbolData.active.includes(symbol)
    const next = isActive
      ? symbolData.active.filter((s) => s !== symbol)
      : [...symbolData.active, symbol]
    if (next.length === 0) {
      toast.error("At least one symbol required")
      return
    }
    try {
      await updateSymbols.mutateAsync(next)
      toast.success(`Trading symbols updated`, {
        description: `Bot will trade ${next.length} symbol${next.length > 1 ? "s" : ""} on next cycle`,
      })
    } catch (e: any) {
      toast.error("Update failed", { description: e.response?.data?.detail || "Could not update symbols" })
    }
  }

  const [localSettings, setLocalSettings] = useState<any>(null)
  const [exchangeProfiles, setExchangeProfiles] = useState<any>({ demo: {}, live: {} })
  const [activeTab, setActiveTab] = useState<'demo' | 'live'>('demo')

  // Refs read DOM values directly on submit — no async state sync issues
  const apiKeyRef = useRef<HTMLInputElement>(null)
  const apiSecretRef = useRef<HTMLInputElement>(null)
  const baseUrlRef = useRef<HTMLInputElement>(null)

  const { data: availableModels, isLoading: isLoadingModels } = useAIModels(localSettings?.ai?.provider)

  useEffect(() => {
    if (initialSettings) setLocalSettings(initialSettings)
  }, [initialSettings])

  useEffect(() => {
    if (profiles) {
      setExchangeProfiles({ demo: profiles.demo || {}, live: profiles.live || {} })
      // Restore base_url into the input on tab switch / load
      if (baseUrlRef.current) {
        baseUrlRef.current.value = profiles[activeTab]?.base_url || ""
      }
    }
  }, [profiles, activeTab])

  // Clear key/secret fields when switching tabs so previous tab's typing doesn't bleed over
  useEffect(() => {
    if (apiKeyRef.current) apiKeyRef.current.value = ""
    if (apiSecretRef.current) apiSecretRef.current.value = ""
    if (baseUrlRef.current) baseUrlRef.current.value = profiles?.[activeTab]?.base_url || ""
  }, [activeTab]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSave = async () => {
    try {
      await Promise.all([
        updateAI.mutateAsync({
          advancedReasoningEnabled: localSettings.advancedReasoningEnabled,
          provider: localSettings.ai.provider,
          model: localSettings.ai.model,
          openai_api_key: localSettings.ai.openai_api_key,
          google_api_key: localSettings.ai.google_api_key,
          anthropic_api_key: localSettings.ai.anthropic_api_key
        }),
        updateNotifications.mutateAsync({
          telegram_bot_token: localSettings.notifications?.telegram_bot_token,
          telegram_chat_id: localSettings.notifications?.telegram_chat_id
        })
      ])
      toast.success("Settings saved successfully")
    } catch (err) {
      toast.error("Error saving settings")
    }
  }

  const handleSelectMode = async (slug: string) => {
    try {
      const result = await setMode.mutateAsync(slug)
      toast.success(`Mode aktif: ${result.name}`, {
        description: result.tagline,
      })
    } catch (e: any) {
      toast.error("Mode change failed", {
        description: e.response?.data?.detail || "Could not switch bot mode.",
      })
    }
  }

  const handleDiscard = () => {
    setLocalSettings(initialSettings)
    toast.info("Changes discarded")
  }

  /** Read directly from DOM refs — guaranteed to reflect what the user actually typed */
  const getFormValues = () => ({
    api_key: apiKeyRef.current?.value?.trim() || "",
    api_secret: apiSecretRef.current?.value?.trim() || "",
    base_url: baseUrlRef.current?.value?.trim() || "",
  })

  const handleTestConnection = async () => {
    const { api_key, api_secret, base_url } = getFormValues()
    // Send "****" when empty so backend falls back to stored credentials
    try {
      await testConn.mutateAsync({
        profile: activeTab,
        api_key: api_key || "****",
        api_secret: api_secret || "****",
        base_url: base_url || exchangeProfiles[activeTab]?.base_url || undefined,
      })
      toast.success(`${activeTab.toUpperCase()} connection successful!`)
    } catch (e: any) {
      toast.error("Connection Failed", {
        description: e.response?.data?.detail || "Could not connect to exchange.",
      })
    }
  }

  const handleSaveProfile = async () => {
    const { api_key, api_secret, base_url } = getFormValues()
    const payload: Record<string, string> = { base_url }
    if (api_key) payload.api_key = api_key
    if (api_secret) payload.api_secret = api_secret

    try {
      await updateProfile.mutateAsync({ profile: activeTab, data: payload })
      // Clear key/secret inputs after save (base_url stays as-is)
      if (apiKeyRef.current) apiKeyRef.current.value = ""
      if (apiSecretRef.current) apiSecretRef.current.value = ""
      toast.success(`${activeTab.toUpperCase()} credentials saved!`)
    } catch (e: any) {
      toast.error("Save Failed", {
        description: e.response?.data?.detail || "Could not save credentials.",
      })
    }
  }

  if (isLoading || !localSettings) {
    return (
      <div className="space-y-8 max-w-4xl animate-in fade-in duration-700">
        <div>
           <h1 className="text-3xl font-bold tracking-tight text-white">System Settings</h1>
           <p className="text-white/40 text-sm mt-1">Loading system configuration...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-8 max-w-4xl animate-in fade-in duration-700">
        <div>
           <h1 className="text-3xl font-bold tracking-tight text-white">System Settings</h1>
           <p className="text-red-500 text-sm mt-1">Error loading settings: {(error as any)?.message || String(error)}</p>
        </div>
      </div>
    )
  }

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
                <div className="grid gap-6 md:grid-cols-2">
                   <div className="grid gap-2">
                      <Label className="text-xs text-white/50 uppercase tracking-widest">Primary Model Provider</Label>
                      <Select 
                        value={localSettings.ai?.provider} 
                        onValueChange={(val) => setLocalSettings({
                          ...localSettings, 
                          ai: { ...localSettings.ai, provider: val, model: "" }
                        })}
                      >
                        <SelectTrigger className="bg-white/5 border-white/10 text-white">
                          <SelectValue placeholder="Select Provider" />
                        </SelectTrigger>
                        <SelectContent className="bg-[#050B0A] border-white/10 text-white">
                          <SelectItem value="openai">OpenAI</SelectItem>
                          <SelectItem value="google">Google Gemini</SelectItem>
                          <SelectItem value="anthropic">Anthropic Claude</SelectItem>
                        </SelectContent>
                      </Select>
                   </div>
                   <div className="grid gap-2">
                      <Label className="text-xs text-white/50 uppercase tracking-widest">Model Selection</Label>
                      <Select 
                        value={localSettings.ai?.model} 
                        onValueChange={(val) => setLocalSettings({
                          ...localSettings, 
                          ai: { ...localSettings.ai, model: val }
                        })}
                        disabled={!localSettings.ai?.provider || isLoadingModels}
                      >
                        <SelectTrigger className="bg-white/5 border-white/10 text-white">
                          <SelectValue placeholder={isLoadingModels ? "Loading models..." : "Select Model"} />
                        </SelectTrigger>
                        <SelectContent className="bg-[#050B0A] border-white/10 text-white">
                          {availableModels?.map((model) => (
                            <SelectItem key={model} value={model}>{model}</SelectItem>
                          ))}
                          {!isLoadingModels && (!availableModels || availableModels.length === 0) && (
                            <SelectItem value="none" disabled>No models available</SelectItem>
                          )}
                        </SelectContent>
                      </Select>
                   </div>
                </div>

                <div className="grid gap-2">
                   <Label className="text-xs text-white/50 uppercase tracking-widest">
                      {localSettings.ai?.provider?.toUpperCase() || "PROVIDER"} API KEY
                   </Label>
                   <Input 
                      type="password" 
                      placeholder="••••••••••••••••"
                      className="bg-white/5 border-white/10 text-white"
                      value={
                         localSettings.ai?.provider === "openai" ? localSettings.ai.openai_api_key :
                         localSettings.ai?.provider === "google" ? localSettings.ai.google_api_key :
                         localSettings.ai?.provider === "anthropic" ? localSettings.ai.anthropic_api_key : ""
                      }
                      onChange={(e) => {
                         const provider = localSettings.ai?.provider;
                         if (provider === "openai") setLocalSettings({...localSettings, ai: {...localSettings.ai, openai_api_key: e.target.value}});
                         if (provider === "google") setLocalSettings({...localSettings, ai: {...localSettings.ai, google_api_key: e.target.value}});
                         if (provider === "anthropic") setLocalSettings({...localSettings, ai: {...localSettings.ai, anthropic_api_key: e.target.value}});
                      }}
                   />
                   <p className="text-[10px] text-white/20 italic">API keys are stored securely and never exposed in logs.</p>
                </div>

               <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/5">
                  <div className="space-y-1">
                     <p className="text-sm font-bold text-white">Advanced Reasoning</p>
                     <p className="text-[10px] text-white/30 uppercase tracking-widest">Use higher-cost models for complex regimes</p>
                  </div>
                  <Switch 
                    checked={localSettings.advancedReasoningEnabled} 
                    onCheckedChange={(val) => setLocalSettings({...localSettings, advancedReasoningEnabled: val})}
                  />
               </div>
            </CardContent>
         </Card>

         {/* Exchange Configuration */}
         <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
            <CardHeader className="flex flex-row items-center justify-between gap-4">
               <div className="flex flex-row items-center gap-4">
                 <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
                    <Key className="w-5 h-5 text-blue-500" />
                 </div>
                 <div>
                    <CardTitle className="text-lg text-white">Exchange API</CardTitle>
                    <CardDescription className="text-white/30">Securely transmit orders to your exchange account.</CardDescription>
                 </div>
               </div>
               <div className="flex bg-white/5 rounded-lg p-1 border border-white/10">
                 <button 
                   onClick={() => setActiveTab('demo')}
                   className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${activeTab === 'demo' ? 'bg-blue-500/20 text-blue-400' : 'text-white/40 hover:text-white'}`}
                 >
                   DEMO
                 </button>
                 <button 
                   onClick={() => setActiveTab('live')}
                   className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${activeTab === 'live' ? 'bg-red-500/20 text-red-400' : 'text-white/40 hover:text-white'}`}
                 >
                   LIVE
                 </button>
               </div>
            </CardHeader>
            <CardContent className="space-y-6 pt-4">
               {/* Warning: live profile has placeholder credentials */}
               {activeTab === 'live' && exchangeProfiles.live?.is_placeholder && (
                 <div className="flex items-start gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                   <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                   <div className="space-y-1">
                     <p className="text-xs font-bold text-red-400">Real Credentials Required</p>
                     <p className="text-[10px] text-red-400/70 leading-relaxed">
                       The LIVE profile is using placeholder/test API keys. Enter your real Bybit mainnet API key and secret below, then save. You will not be able to switch to LIVE mode until valid credentials are configured.
                     </p>
                   </div>
                 </div>
               )}
               <div className="grid gap-6 md:grid-cols-2">
                  {/* API Key — uncontrolled, read via ref on save */}
                  <div className="grid gap-2">
                     <div className="flex items-center justify-between">
                       <Label className="text-xs text-white/50 uppercase tracking-widest">API Key</Label>
                       {exchangeProfiles[activeTab]?.api_key && !exchangeProfiles[activeTab]?.is_placeholder && (
                         <span className="text-[9px] font-bold text-emerald-500/70 bg-emerald-500/10 px-2 py-0.5 rounded uppercase tracking-widest">✓ Stored</span>
                       )}
                       {exchangeProfiles[activeTab]?.is_placeholder && (
                         <span className="text-[9px] font-bold text-red-400/80 bg-red-500/10 px-2 py-0.5 rounded uppercase tracking-widest">⚠ Invalid</span>
                       )}
                     </div>
                     <input
                       ref={apiKeyRef}
                       type="text"
                       placeholder={exchangeProfiles[activeTab]?.api_key && !exchangeProfiles[activeTab]?.is_placeholder ? "Leave blank to keep existing" : "Enter API Key"}
                       className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
                       autoComplete="off"
                       spellCheck={false}
                     />
                  </div>

                  {/* API Secret — uncontrolled, read via ref on save */}
                  <div className="grid gap-2">
                     <div className="flex items-center justify-between">
                       <Label className="text-xs text-white/50 uppercase tracking-widest">API Secret</Label>
                       {exchangeProfiles[activeTab]?.api_key && !exchangeProfiles[activeTab]?.is_placeholder && (
                         <span className="text-[9px] font-bold text-emerald-500/70 bg-emerald-500/10 px-2 py-0.5 rounded uppercase tracking-widest">✓ Stored</span>
                       )}
                       {exchangeProfiles[activeTab]?.is_placeholder && (
                         <span className="text-[9px] font-bold text-red-400/80 bg-red-500/10 px-2 py-0.5 rounded uppercase tracking-widest">⚠ Invalid</span>
                       )}
                     </div>
                     <input
                       ref={apiSecretRef}
                       type="password"
                       placeholder={exchangeProfiles[activeTab]?.api_key && !exchangeProfiles[activeTab]?.is_placeholder ? "Leave blank to keep existing" : "Enter API Secret"}
                       className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
                       autoComplete="new-password"
                       spellCheck={false}
                     />
                  </div>

                  {/* Base URL */}
                  <div className="grid gap-2 md:col-span-2">
                     <Label className="text-xs text-white/50 uppercase tracking-widest">Base URL (Optional)</Label>
                     <input
                       ref={baseUrlRef}
                       type="text"
                       defaultValue={exchangeProfiles[activeTab]?.base_url || ""}
                       placeholder={activeTab === 'demo' ? "https://api-demo.bybit.com" : "https://api.bybit.com (or leave blank for mainnet)"}
                       className="flex h-10 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm font-mono text-white placeholder:text-white/30 focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
                     />
                     <p className="text-[9px] text-white/20">
                       {activeTab === 'demo' ? "Bybit Demo Trading endpoint: https://api-demo.bybit.com" : "Bybit Mainnet: leave blank or enter https://api.bybit.com"}
                     </p>
                  </div>
               </div>
               <div className="flex items-center justify-between pt-4 border-t border-white/5">
                  <div className="text-xs font-bold flex items-center gap-2">
                    {exchangeProfiles[activeTab]?.is_active ? (
                      <span className="text-emerald-400 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        Active Profile
                      </span>
                    ) : (
                      <span className="text-white/40">Inactive</span>
                    )}
                  </div>
                  <div className="flex gap-3">
                     <Button 
                      variant="outline" 
                      onClick={handleTestConnection}
                      disabled={testConn.isPending}
                      className="text-xs font-bold border-white/10 text-white/70 hover:text-white"
                    >
                      {testConn.isPending ? "Testing..." : "Test Connection"}
                    </Button>
                    <Button 
                      onClick={handleSaveProfile}
                      disabled={updateProfile.isPending}
                      className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow-[0_0_15px_rgba(37,99,235,0.2)]"
                    >
                      {updateProfile.isPending ? "Saving..." : "Save Credentials"}
                    </Button>
                  </div>
               </div>
            </CardContent>
         </Card>

         {/* Bot Mode Picker — replaces individual risk-parameter inputs */}
         <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
            <CardHeader className="flex flex-row items-center gap-4">
               <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                  <Sliders className="w-5 h-5 text-red-500" />
               </div>
               <div>
                  <CardTitle className="text-lg text-white">Bot Mode</CardTitle>
                  <CardDescription className="text-white/30">
                     Pilih profil risiko bot — semakin agresif, semakin sering trade dan semakin besar potensi profit & loss.
                  </CardDescription>
               </div>
            </CardHeader>
            <CardContent className="space-y-3">
               {!modeData ? (
                  <div className="p-6 text-center text-[10px] text-white/30 uppercase tracking-widest">Loading modes...</div>
               ) : (
                  modeData.profiles.map((profile: ModeProfile) => {
                     const isActive = profile.slug === modeData.active_slug
                     const Icon = MODE_ICONS[profile.icon] || Shield
                     const color = MODE_COLORS[profile.color] || MODE_COLORS.blue
                     return (
                        <button
                           key={profile.slug}
                           onClick={() => handleSelectMode(profile.slug)}
                           disabled={setMode.isPending}
                           className={`w-full text-left rounded-xl border-2 p-4 transition-all hover:bg-white/[0.02] disabled:opacity-50 ${
                              isActive ? `${color.border} ${color.bg} ring-1 ${color.ring}` : "border-white/5 bg-transparent"
                           }`}
                        >
                           <div className="flex items-start gap-4">
                              <div className={`p-2 rounded-lg ${color.bg} border ${color.border} shrink-0`}>
                                 <Icon className={`w-5 h-5 ${color.text}`} />
                              </div>
                              <div className="flex-1 min-w-0">
                                 <div className="flex items-center gap-2 mb-1">
                                    <span className={`text-sm font-bold ${isActive ? color.text : "text-white"}`}>
                                       {profile.name}
                                    </span>
                                    <span className="text-[9px] font-bold text-white/30 uppercase tracking-widest">
                                       Level {profile.risk_level}/5
                                    </span>
                                    {isActive && (
                                       <span className={`flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest ${color.text}`}>
                                          <Check className="w-3 h-3" /> Aktif
                                       </span>
                                    )}
                                 </div>
                                 <p className={`text-xs leading-relaxed ${isActive ? "text-white/70" : "text-white/40"}`}>
                                    {profile.tagline}
                                 </p>
                                 {isActive && (
                                    <p className="text-[10px] text-white/40 leading-relaxed mt-2 italic">
                                       {profile.description}
                                    </p>
                                 )}
                              </div>
                           </div>
                        </button>
                     )
                  })
               )}
               <p className="text-[10px] text-white/30 italic pt-2 border-t border-white/5">
                 💡 Detail parameter dari mode yang aktif bisa dilihat di halaman <b className="text-emerald-500/60">AI Agents</b>.
               </p>
            </CardContent>
         </Card>

         {/* Trading Symbols */}
         <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
            <CardHeader className="flex flex-row items-center gap-4">
               <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                  <Coins className="w-5 h-5 text-amber-500" />
               </div>
               <div>
                  <CardTitle className="text-lg text-white">Trading Symbols</CardTitle>
                  <CardDescription className="text-white/30">
                     Pilih koin mana saja yang akan dianalisa dan diperdagangkan oleh bot tiap cycle.
                  </CardDescription>
               </div>
            </CardHeader>
            <CardContent className="space-y-3">
               {!symbolData ? (
                  <div className="p-6 text-center text-[10px] text-white/30 uppercase tracking-widest">Loading symbols...</div>
               ) : (
                  symbolData.supported.map((sym) => {
                     const isActive = symbolData.active.includes(sym.symbol)
                     return (
                        <button
                           key={sym.symbol}
                           onClick={() => handleToggleSymbol(sym.symbol)}
                           disabled={updateSymbols.isPending}
                           className={`w-full text-left rounded-xl border-2 p-4 transition-all hover:bg-white/[0.02] disabled:opacity-50 flex items-center gap-3 ${
                              isActive ? "border-emerald-500/30 bg-emerald-500/5" : "border-white/5 bg-transparent"
                           }`}
                        >
                           <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 ${
                             isActive ? "bg-emerald-500 border-emerald-500" : "border-white/20"
                           }`}>
                              {isActive && <Check className="w-3.5 h-3.5 text-black" />}
                           </div>
                           <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                 <span className={`text-sm font-bold ${isActive ? "text-emerald-400" : "text-white"}`}>
                                    {sym.name}
                                 </span>
                                 <span className="text-[10px] font-mono text-white/30">{sym.ticker}/USDT</span>
                              </div>
                              <p className="text-[10px] text-white/40 leading-relaxed mt-0.5">
                                 On-chain source: <span className="text-white/60">{sym.onchain_source}</span>
                              </p>
                           </div>
                        </button>
                     )
                  })
               )}
               <p className="text-[10px] text-white/30 italic pt-2 border-t border-white/5">
                 ℹ️ Bot akan iterasi tiap simbol pada setiap cycle (~60 detik). Lebih banyak simbol = lebih banyak peluang trade.
               </p>
            </CardContent>
         </Card>

         {/* Notifications Configuration */}
         <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
            <CardHeader className="flex flex-row items-center gap-4">
               <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20">
                  <Bell className="w-5 h-5 text-purple-500" />
               </div>
               <div>
                  <CardTitle className="text-lg text-white">Notifications</CardTitle>
                  <CardDescription className="text-white/30">Connect Telegram to receive real-time alerts and reports.</CardDescription>
               </div>
            </CardHeader>
            <CardContent className="space-y-6">
               <div className="grid md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                     <Label className="text-[10px] text-white/50 uppercase tracking-widest">Telegram Bot Token</Label>
                     <Input 
                        type="password" 
                        placeholder={localSettings.notifications?.telegram_bot_token === "****" ? "••••••••••••••••" : "Enter Bot Token"}
                        value={localSettings.notifications?.telegram_bot_token || ""} 
                        onChange={(e) => setLocalSettings({
                          ...localSettings, 
                          notifications: { ...localSettings.notifications, telegram_bot_token: e.target.value }
                        })}
                        className="bg-white/5 border-white/10 text-white font-mono" 
                     />
                  </div>
                  <div className="space-y-2">
                     <Label className="text-[10px] text-white/50 uppercase tracking-widest">Telegram Chat ID</Label>
                     <Input 
                        type="text" 
                        placeholder="Enter Chat ID"
                        value={localSettings.notifications?.telegram_chat_id || ""} 
                        onChange={(e) => setLocalSettings({
                          ...localSettings, 
                          notifications: { ...localSettings.notifications, telegram_chat_id: e.target.value }
                        })}
                        className="bg-white/5 border-white/10 text-white font-mono" 
                     />
                  </div>
               </div>
               <div className="flex items-center justify-between pt-2">
                 <p className="text-[10px] text-white/20 italic">
                   Get your Chat ID by messaging <code className="text-emerald-500/50">@userinfobot</code> on Telegram.
                 </p>
                 <Button
                   variant="outline"
                   size="sm"
                   onClick={async () => {
                     try {
                       await testTelegram.mutateAsync()
                       toast.success("Test message sent — check Telegram")
                     } catch (e: any) {
                       toast.error("Test Failed", { description: e.response?.data?.detail || "Could not send test message." })
                     }
                   }}
                   disabled={testTelegram.isPending}
                   className="text-xs font-bold border-purple-500/30 text-purple-400 hover:bg-purple-500/10"
                 >
                   {testTelegram.isPending ? "Sending..." : "Send Test Message"}
                 </Button>
               </div>
               <div className="rounded-lg bg-purple-500/5 border border-purple-500/10 p-3 text-[10px] text-purple-200/60 leading-relaxed">
                 <b className="text-purple-300">Notifications you'll receive:</b><br/>
                 • <b>Real-time:</b> Every execution decision (LONG/SHORT) with full agent breakdown<br/>
                 • <b>Daily 07:00 WIB:</b> Total Equity, PnL Today, Win Rate, trades summary
               </div>
            </CardContent>
         </Card>

         {/* Audit Logs */}
         <Card className="bg-[#050B0A]/50 border-white/5 backdrop-blur-md">
            <CardHeader className="flex flex-row items-center gap-4">
               <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                  <History className="w-5 h-5 text-amber-500" />
               </div>
               <div>
                  <CardTitle className="text-lg text-white">Security Audit Log</CardTitle>
                  <CardDescription className="text-white/30">Recent administrative actions and configuration changes.</CardDescription>
               </div>
            </CardHeader>
            <CardContent className="p-0">
               <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                     <thead>
                        <tr className="border-b border-white/5 text-[9px] font-bold text-white/20 uppercase tracking-widest">
                           <th className="px-6 py-3">Timestamp</th>
                           <th className="px-6 py-3">Action</th>
                           <th className="px-6 py-3">User</th>
                           <th className="px-6 py-3">IP Address</th>
                        </tr>
                     </thead>
                     <tbody className="divide-y divide-white/[0.02]">
                        {auditLogs?.map((log) => (
                           <tr key={log.id} className="hover:bg-white/[0.01] transition-colors">
                              <td className="px-6 py-3 text-[10px] text-white/40 font-mono">
                                 {new Date(log.timestamp).toLocaleString(typeof navigator !== "undefined" ? navigator.language : undefined)}
                              </td>
                              <td className="px-6 py-3">
                                 <span className="text-[10px] font-bold text-white/60">{log.action.replace('settings_update_', '').toUpperCase()}</span>
                              </td>
                              <td className="px-6 py-3 text-[10px] text-white/40">{log.user_id}</td>
                              <td className="px-6 py-3 text-[10px] text-white/20 font-mono">{log.ip_address || "N/A"}</td>
                           </tr>
                        ))}
                        {(!auditLogs || auditLogs.length === 0) && (
                           <tr>
                              <td colSpan={4} className="px-6 py-8 text-center text-[10px] text-white/20 uppercase tracking-widest">
                                 No recent activity
                              </td>
                           </tr>
                        )}
                     </tbody>
                  </table>
               </div>
            </CardContent>
         </Card>
      </div>

      <div className="flex justify-end gap-3 pb-12">
         <Button 
            variant="ghost" 
            onClick={handleDiscard}
            className="text-white/40 hover:text-white"
         >
            Discard Changes
         </Button>
         <Button 
            onClick={handleSave}
            disabled={updateAI.isPending || updateNotifications.isPending}
            className="bg-emerald-500 hover:bg-emerald-400 text-black font-bold shadow-[0_0_20px_rgba(16,185,129,0.2)]"
         >
            {updateAI.isPending || updateNotifications.isPending ? "Saving..." : "Save System Configuration"}
         </Button>
      </div>
    </div>
  )
}
