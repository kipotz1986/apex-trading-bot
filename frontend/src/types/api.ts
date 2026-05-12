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
  id: number;
  symbol: string;
  side: "LONG" | "SHORT" | "BUY" | "SELL";
  size: number;
  entry: number;
  current: number;
  leverage: number;
  pnl: number;
  pnl_percent: number | null;
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
  amount?: number;
  entry_price: number;
  exit_price: number;
  pnl_usd: number;
  status: string;
  created_at: string;
  meta_data: any;
}

export interface AgentScore {
  agent_name: string;
  accuracy_score: number;
  total_predictions: number;
  successful_predictions: number;
  score: number;
  weight: number;
  status: "CALIBRATING" | "LEARNING" | "STABLE" | "OPTIMIZED" | "STRUGGLING";
  last_updated: string;
}

export interface AgentDecision {
  id: number;
  timestamp: string;
  symbol: string;
  action: string;
  reasoning: string;
  consensus_score: number;
  confidence?: number;
  market_regime?: string;
  agent_signals: any;
}

export interface TradeStats {
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  total_pnl: number;
  avg_trade_pnl: number;
}

export interface PromptDetails {
  prompt_input: string;
  prompt_output: string;
  model_name: string;
  agent_name?: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface ExternalApiDetails {
  url?: string;
  method?: string;
  request_body?: string;
  response_body?: string;
  headers?: string;
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
  prompt_details?: PromptDetails;
  external_api_details?: ExternalApiDetails;
}
