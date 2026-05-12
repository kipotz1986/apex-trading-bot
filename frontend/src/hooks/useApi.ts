import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
  PortfolioSummary,
  OpenPosition,
  BotStatus,
  AgentInsights,
  Trade,
  AgentScore,
  AgentDecision,
  IntegrationLog,
  TradeStats
} from "@/types/api";

export const usePortfolioSummary = () => {
  return useQuery<PortfolioSummary>({
    queryKey: ["portfolio", "summary"],
    queryFn: async () => {
      const { data } = await api.get("/portfolio/summary");
      return data;
    },
    refetchInterval: 30000,
  });
};

export const useOpenPositions = () => {
  return useQuery<OpenPosition[]>({
    queryKey: ["portfolio", "positions"],
    queryFn: async () => {
      const { data } = await api.get("/portfolio/positions");
      return data;
    },
    refetchInterval: 30000,
  });
};

export const useClosePosition = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (orderId: number) => api.post(`/portfolio/close/${orderId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });
};

export const useBotStatus = () => {
  return useQuery<BotStatus>({
    queryKey: ["bot", "status"],
    queryFn: async () => {
      const { data } = await api.get("/bot/status");
      return data;
    },
  });
};

export const useAgentInsights = () => {
  return useQuery<AgentInsights>({
    queryKey: ["agents", "insights"],
    queryFn: async () => {
      const { data } = await api.get("/agents/insights");
      return data;
    },
    refetchInterval: 30000,
  });
};

export const useToggleBot = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (action: "start" | "stop") => {
      await api.post(`/bot/${action}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bot", "status"] });
    },
  });
};

export const useChangeMode = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (mode: "live" | "paper") => {
      await api.post("/bot/mode", { mode });
    },
    onSuccess: () => {
      // Invalidate everything — balance, positions, trades, status all belong to the new profile
      queryClient.invalidateQueries();
    },
  });
};

export const useEquityHistory = (hours: number = 24) => {
  return useQuery({
    queryKey: ["portfolio", "history", hours],
    queryFn: async () => {
      const { data } = await api.get("/portfolio/equity-history", { params: { hours } });
      return data;
    },
  });
};

export const useTradeHistory = (page = 1, per_page = 25, symbol?: string, side?: string) => {
  return useQuery<{total: number, trades: Trade[]}>({
    queryKey: ["trades", "history", page, per_page, symbol, side],
    queryFn: async () => {
      const { data } = await api.get("/trades/", { params: { page, per_page, symbol, side } });
      return data;
    },
  });
};

export const useTradeStats = () => {
  return useQuery<TradeStats & { avg_trade: number }>({
    queryKey: ["trades", "stats"],
    queryFn: async () => {
      const { data } = await api.get("/trades/stats");
      return data;
    },
  });
};

export const useTradeDetail = (tradeId: number | null) => {
  return useQuery<Trade & { meta_data: any }>({
    queryKey: ["trades", "detail", tradeId],
    queryFn: async () => {
      const { data } = await api.get(`/trades/${tradeId}`);
      return data;
    },
    enabled: tradeId !== null,
  });
};

export const useAgentScores = () => {
  return useQuery<AgentScore[]>({
    queryKey: ["agents", "scores"],
    queryFn: async () => {
      const { data } = await api.get("/agents/scores");
      return data;
    },
  });
};

export const useAgentDecisions = (limit = 20) => {
  return useQuery<AgentDecision[]>({
    queryKey: ["agents", "decisions", limit],
    queryFn: async () => {
      const { data } = await api.get("/agents/decisions", { params: { limit } });
      return data;
    },
    refetchInterval: 10000,
  });
};

export const useLearningStats = () => {
  return useQuery<{patterns_learned: number, model_version: string, training_cycles: string, rl_reward_score: number}>({
    queryKey: ["agents", "learning"],
    queryFn: async () => {
      const { data } = await api.get("/agents/learning");
      return data;
    },
  });
};

export interface EvolutionEvent {
  id: string;
  timestamp: string;
  event_type: string;
  title: string;
  description: string;
  metrics?: Record<string, any>;
}

export const useStrategyEvolution = () => {
  return useQuery<EvolutionEvent[]>({
    queryKey: ["agents", "evolution"],
    queryFn: async () => {
      const { data } = await api.get("/agents/evolution");
      return data;
    },
    refetchInterval: 30000,
  });
};


export const useConsensusStatus = () => {
  return useQuery<{
    agreement_rate: number;
    avg_consensus_score: number;
    total_decisions: number;
    status: string;
  }>({
    queryKey: ["agents", "consensus-status"],
    queryFn: async () => {
      const { data } = await api.get("/agents/consensus-status");
      return data;
    },
    refetchInterval: 30000,
  });
};


export const useBacktest = () => {
  return useMutation({
    mutationFn: async (params: { symbol: string, timeframe: string, start_date: string, end_date: string, initial_balance: number }) => {
      const { data } = await api.post("/backtest/run", params);
      return data;
    },
  });
};

export const useIntegrationLogs = (page: number = 1, perPage: number = 50, serviceType?: string, status?: string) => {
  return useQuery<{total: number, page: number, per_page: number, logs: IntegrationLog[]}>({
    queryKey: ["logs", "integration", page, perPage, serviceType, status],
    queryFn: async () => {
      const { data } = await api.get("/logs/integration", {
        params: { page, per_page: perPage, service_type: serviceType, status }
      });
      return data;
    },
  });
};

// System Settings
export interface SystemSettingsData {
  dailyLossLimit: number;
  maxLeverage: number;
  maxPositionSize: number;
  maxTotalExposure: number;
  consensusThresholdStrong: number;
  consensusThresholdModerate: number;
  aiProvider: string;
  advancedReasoningEnabled: boolean;
  tradingSymbols: string[];
  ai: {
    provider: string;
    model: string;
    openai_api_key: string;
    google_api_key: string;
    anthropic_api_key: string;
  };
  exchange: {
    name: string;
    api_key: string;
    testnet: boolean;
  };
  notifications?: {
    telegram_bot_token: string;
    telegram_chat_id: string;
  };
}

export interface ExchangeProfile {
  exchange: string;
  api_key: string;
  api_secret?: string;
  base_url?: string;
  is_active: boolean;
}

export const useSystemSettings = () => {
  return useQuery<SystemSettingsData>({
    queryKey: ["settings", "all"],
    queryFn: async () => {
      const { data } = await api.get("/settings/");
      return data;
    },
  });
};

export const useAIModels = (provider?: string) => {
  return useQuery<string[]>({
    queryKey: ["settings", "ai", "models", provider],
    queryFn: async () => {
      if (!provider) return [];
      const { data } = await api.get(`/settings/ai/models/${provider}`);
      return data;
    },
    enabled: !!provider,
  });
};

export const useUpdateAISettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { 
      advancedReasoningEnabled: boolean, 
      provider?: string, 
      model?: string,
      openai_api_key?: string,
      google_api_key?: string,
      anthropic_api_key?: string
    }) => {
      await api.put("/settings/ai", payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "all"] });
    },
  });
};

export const useUpdateRiskSettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { 
      dailyLossLimit: number, 
      maxLeverage: number, 
      maxPositionSize: number,
      consensusThresholdStrong: number,
      consensusThresholdModerate: number
    }) => {
      await api.put("/settings/risk", payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "all"] });
    },
  });
};

export const useUpdateNotificationSettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { 
      telegram_bot_token?: string, 
      telegram_chat_id?: string 
    }) => {
      await api.put("/settings/notifications", payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "all"] });
    },
  });
};

export const useExchangeProfiles = () => {
  return useQuery<Record<string, ExchangeProfile>>({
    queryKey: ["settings", "exchange", "profiles"],
    queryFn: async () => {
      const { data } = await api.get("/settings/exchange/profiles");
      return data;
    },
  });
};

export const useUpdateExchangeProfile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ profile, data }: { profile: string, data: Partial<ExchangeProfile> }) => {
      await api.put(`/settings/exchange/profiles/${profile}`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "exchange", "profiles"] });
    },
  });
};

export const useTestExchangeConnection = () => {
  return useMutation({
    mutationFn: async (payload: { profile: string, api_key?: string, api_secret?: string, base_url?: string }) => {
      const { data } = await api.post("/settings/exchange/test-connection", payload);
      return data;
    },
  });
};

export const useTestTelegram = () => {
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/settings/notifications/test");
      return data;
    },
  });
};

// Bot Mode Profiles
export interface ModeParamDetail {
  key: string;
  value: string;
  label: string;
  explanation: string;
  unit: string;
}

export interface ModeProfile {
  slug: string;
  name: string;
  name_en: string;
  tagline: string;
  description: string;
  icon: string;
  color: string;
  risk_level: number;
  params: Record<string, string>;
  param_details: ModeParamDetail[];
}

export const useModeProfiles = () => {
  return useQuery<{ active_slug: string; profiles: ModeProfile[] }>({
    queryKey: ["settings", "mode-profiles"],
    queryFn: async () => {
      const { data } = await api.get("/settings/mode-profiles");
      return data;
    },
  });
};

export const useActiveModeProfile = () => {
  return useQuery<ModeProfile>({
    queryKey: ["settings", "mode-profiles", "active"],
    queryFn: async () => {
      const { data } = await api.get("/settings/mode-profiles/active");
      return data;
    },
    refetchInterval: 60000,
  });
};

export const useSetModeProfile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (slug: string) => {
      const { data } = await api.post(`/settings/mode-profiles/${slug}`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });
};

// Trading Symbols
export interface SupportedSymbol {
  symbol: string;
  name: string;
  ticker: string;
  onchain_source: string;
}

export const useTradingSymbols = () => {
  return useQuery<{ active: string[]; supported: SupportedSymbol[] }>({
    queryKey: ["settings", "trading-symbols"],
    queryFn: async () => {
      const { data } = await api.get("/settings/trading-symbols");
      return data;
    },
  });
};

export const useUpdateTradingSymbols = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (symbols: string[]) => {
      const { data } = await api.put("/settings/trading-symbols", { symbols });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });
};

export interface AuditLog {
  id: number;
  timestamp: string;
  action: string;
  user_id: string;
  details: any;
  ip_address?: string;
}

export const useAuditLogs = (limit = 20) => {
  return useQuery<AuditLog[]>({
    queryKey: ["settings", "audit-logs", limit],
    queryFn: async () => {
      const { data } = await api.get("/settings/audit-logs", { params: { limit } });
      return data;
    },
    refetchInterval: 60000,
  });
};
