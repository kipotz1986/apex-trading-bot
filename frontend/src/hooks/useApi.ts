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
  IntegrationLog
} from "@/types/api";

export const usePortfolioSummary = () => {
  return useQuery<PortfolioSummary>({
    queryKey: ["portfolio", "summary"],
    queryFn: async () => {
      const { data } = await api.get("/portfolio/summary");
      return data;
    },
    refetchInterval: 10000,
  });
};

export const useOpenPositions = () => {
  return useQuery<OpenPosition[]>({
    queryKey: ["portfolio", "positions"],
    queryFn: async () => {
      const { data } = await api.get("/portfolio/positions");
      return data;
    },
    refetchInterval: 5000,
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
      queryClient.invalidateQueries({ queryKey: ["bot", "status"] });
    },
  });
};

export const useEquityHistory = () => {
  return useQuery({
    queryKey: ["portfolio", "history"],
    queryFn: async () => {
      const { data } = await api.get("/portfolio/equity-history");
      return data;
    },
  });
};

export const useTradeHistory = (page = 1, per_page = 25) => {
  return useQuery<{total: number, trades: Trade[]}>({
    queryKey: ["trades", "history", page, per_page],
    queryFn: async () => {
      const { data } = await api.get("/trades/", { params: { page, per_page } });
      return data;
    },
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
