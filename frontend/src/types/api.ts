export interface PortfolioSummary {
  balance: number;
  equity: number;
  unrealized_pnl: number;
  daily_pnl: number;
  total_pnl: number;
  win_rate: number;
  total_trades: number;
  system_status: string;
  mode: string;
}

export interface OpenPosition {
  id: string;
  symbol: string;
  side: "LONG" | "SHORT";
  size: number;
  entry: number;
  current: number;
  leverage: number;
  pnl: number;
  pnl_percent: number;
  status: "profit" | "loss";
}

export interface BotStatus {
  status: string;
  mode: "LIVE" | "PAPER";
  last_updated: string;
  is_live_enabled: boolean;
}

export interface AgentInsights {
  narrative: string;
  scores: {
    technical: number;
    sentiment: number;
    onchain: number;
  };
}

export interface Trade {
  id: number;
  symbol: string;
  side: string;
  amount: number;
  entry_price: number;
  exit_price: number;
  pnl_usd: number;
  status: string;
  created_at: string;
  meta_data: any;
}

export interface AgentScore {
  id: number;
  agent_name: string;
  accuracy_score: number;
  total_predictions: number;
  last_updated: string;
}

export interface AgentDecision {
  id: number;
  timestamp: string;
  symbol: string;
  action: string;
  reasoning: string;
  consensus_score: number;
  agent_signals: any;
}

export interface IntegrationLog {
  id: number;
  timestamp: string;
  service_type: string;
  provider_name: string;
  endpoint: string;
  status: "SUCCESS" | "ERROR";
  latency_ms: number;
  error_details?: string;
}
