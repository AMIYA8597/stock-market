import { z } from "zod";

// ─── Auth Types ──────────────────────────────────────────────

export const userRegisterSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(128),
  full_name: z.string().min(1).max(255),
  role: z.enum(["admin", "researcher", "analyst", "viewer"]).default("viewer"),
});
export type UserRegister = z.infer<typeof userRegisterSchema>;

export const userLoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});
export type UserLogin = z.infer<typeof userLoginSchema>;

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  role: "admin" | "researcher" | "analyst" | "viewer" | "api_user";
  is_active: boolean;
  is_2fa_enabled: boolean;
  created_at: string;
  last_login_at: string | null;
}

// ─── Market Data Types ───────────────────────────────────────

export interface Quote {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  high: number;
  low: number;
  open: number;
  previous_close: number;
  timestamp: string;
}

export interface OHLCVBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjusted_close?: number;
}

export interface HistoryResponse {
  symbol: string;
  interval: string;
  bars: OHLCVBar[];
  count: number;
}

export type Timeframe = "1m" | "5m" | "15m" | "1h" | "4h" | "1D" | "1W" | "1M";

export type ChartType =
  | "candlestick"
  | "bar"
  | "line"
  | "area"
  | "heikin-ashi"
  | "baseline";

export interface TickData {
  symbol: string;
  price: number;
  volume: number;
  change_pct: number;
  timestamp: string;
}

// ─── Screener Types ──────────────────────────────────────────

export const screenerFilterSchema = z.object({
  asset_class: z.string().optional(),
  exchange: z.string().optional(),
  sector: z.string().optional(),
  min_market_cap: z.number().optional(),
  max_market_cap: z.number().optional(),
  min_price: z.number().optional(),
  max_price: z.number().optional(),
  rsi_min: z.number().min(0).max(100).optional(),
  rsi_max: z.number().min(0).max(100).optional(),
  above_sma_200: z.boolean().optional(),
  volume_surge: z.boolean().optional(),
  ml_confidence_min: z.number().min(0).max(100).optional(),
  sort_by: z.string().default("market_cap"),
  sort_order: z.enum(["asc", "desc"]).default("desc"),
  limit: z.number().min(1).max(500).default(50),
  offset: z.number().min(0).default(0),
});
export type ScreenerFilter = z.infer<typeof screenerFilterSchema>;

export interface ScreenerResult {
  symbol: string;
  name: string;
  asset_class: string;
  exchange: string | null;
  sector: string | null;
  price: number;
  change_percent: number;
  volume: number;
  market_cap: number | null;
  rsi: number | null;
  ml_signal: string | null;
  ml_confidence: number | null;
}

export interface ScreenerResponse {
  results: ScreenerResult[];
  total: number;
  limit: number;
  offset: number;
}

// ─── Prediction Types ────────────────────────────────────────

export interface Prediction {
  symbol: string;
  model_name: string;
  model_version: string;
  prediction_time: string;
  horizon_days: number;
  predicted_price: number;
  predicted_direction: 1 | -1 | 0;
  confidence: number;
  lower_80: number;
  upper_80: number;
  lower_95: number;
  upper_95: number;
  feature_importances: Record<string, number> | null;
  actual_price: number | null;
}

export interface ModelEnsemble {
  symbol: string;
  models: {
    name: string;
    prediction: number;
    direction: 1 | -1 | 0;
    confidence: number;
    weight: number;
  }[];
  consensus_direction: 1 | -1 | 0;
  consensus_confidence: number;
}

// ─── Portfolio Types ─────────────────────────────────────────

export interface Holding {
  symbol: string;
  quantity: number;
  avg_cost: number;
  current_price: number | null;
  market_value: number | null;
  pnl: number | null;
  pnl_percent: number | null;
  weight: number | null;
  day_change: number | null;
  day_change_pct: number | null;
  var_contribution: number | null;
  model_signal: string | null;
  added_at: string;
}

export interface Portfolio {
  id: number;
  name: string;
  description: string | null;
  initial_capital: number;
  holdings: Holding[];
  total_value: number | null;
  total_pnl: number | null;
  total_pnl_pct: number | null;
  created_at: string;
}

export interface RiskMetrics {
  var_95: number;
  var_99: number;
  cvar_95: number;
  max_drawdown: number;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  beta: number | null;
  alpha: number | null;
  correlation_matrix: Record<string, Record<string, number>> | null;
}

export interface OptimizeRequest {
  portfolio_id: number;
  method: "max_sharpe" | "min_volatility" | "efficient_risk" | "hrp";
  risk_free_rate?: number;
  target_return?: number;
}

export interface OptimizeResponse {
  method: string;
  weights: Record<string, number>;
  expected_return: number;
  expected_volatility: number;
  sharpe_ratio: number;
}

// ─── Backtesting Types ───────────────────────────────────────

export type StrategyName =
  | "kalman_pairs"
  | "adaptive_momentum"
  | "ml_alpha"
  | "stat_arb"
  | "volatility_regime"
  | "deep_rl";

export interface BacktestConfig {
  strategy: StrategyName;
  symbols: string[];
  start_date: string;
  end_date: string;
  initial_capital: number;
  benchmark: string;
  include_costs: boolean;
  allow_short: boolean;
  params: Record<string, number | string | boolean>;
}

export interface BacktestMetrics {
  cagr: number;
  total_return: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  max_drawdown: number;
  max_drawdown_duration_days: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  avg_hold_period_days: number;
  alpha: number;
  beta: number;
}

export interface BacktestResult {
  config: BacktestConfig;
  metrics: BacktestMetrics;
  equity_curve: { date: string; value: number; benchmark: number }[];
  drawdown_curve: { date: string; drawdown: number }[];
  monthly_returns: { year: number; month: number; return_pct: number }[];
  trade_log: BacktestTrade[];
  significance: {
    mc_p_value: number;
    bootstrap_sharpe_ci: [number, number];
    deflated_sharpe: number;
  };
}

export interface BacktestTrade {
  id: number;
  date: string;
  symbol: string;
  side: "BUY" | "SELL";
  price: number;
  quantity: number;
  pnl: number;
  duration_days: number;
}

// ─── Alert Types ─────────────────────────────────────────────

export type AlertType =
  | "price"
  | "technical"
  | "ml_signal"
  | "sentiment"
  | "anomaly"
  | "news";

export type AlertSeverity = 1 | 2 | 3 | 4 | 5;

export type AlertChannel = "in_app" | "email" | "webhook";

export interface AlertDefinition {
  id: string;
  name: string;
  symbol: string | null;
  alert_type: AlertType;
  conditions: Record<string, unknown>;
  channels: AlertChannel[];
  cooldown_minutes: number;
  is_active: boolean;
  times_triggered: number;
  last_triggered_at: string | null;
  created_at: string;
}

export interface AlertEvent {
  id: string;
  alert_id: string;
  alert_name: string;
  symbol: string;
  alert_type: AlertType;
  severity: AlertSeverity;
  message: string;
  payload: Record<string, unknown>;
  triggered_at: string;
}

// ─── Research Types ──────────────────────────────────────────

export type RegimeState = "bull" | "bear" | "sideways";

export interface RegimeData {
  symbol: string;
  current_regime: RegimeState;
  confidence: number;
  regime_history: { date: string; regime: RegimeState; probability: number }[];
  transition_matrix: number[][];
}

export interface CorrelationNode {
  id: string;
  symbol: string;
  sector: string;
  market_cap: number;
  x?: number;
  y?: number;
  z?: number;
}

export interface CorrelationEdge {
  source: string;
  target: string;
  weight: number;
  type: "correlation" | "supply_chain" | "sector";
}

export interface ResearchReport {
  symbol: string;
  generated_at: string;
  confidence_score: number;
  technical_view: string;
  fundamental_view: string;
  news_catalysts: string;
  risk_factors: string;
  contradictions: string | null;
  agents_agreement: number;
}

// ─── WebSocket Message Types ─────────────────────────────────

export type WSMessageType =
  | "tick"
  | "prediction_update"
  | "alert_triggered"
  | "regime_change"
  | "anomaly_detected"
  | "portfolio_update"
  | "heartbeat";

export interface WSTickMessage {
  type: "tick";
  symbol: string;
  price: number;
  volume: number;
  change_pct: number;
  timestamp: string;
}

export interface WSPredictionMessage {
  type: "prediction_update";
  symbol: string;
  model: string;
  direction: 1 | -1 | 0;
  confidence: number;
}

export interface WSAlertMessage {
  type: "alert_triggered";
  alert_id: string;
  message: string;
  severity: AlertSeverity;
  symbol: string;
}

export interface WSRegimeMessage {
  type: "regime_change";
  symbol: string;
  old_regime: RegimeState;
  new_regime: RegimeState;
  confidence: number;
}

export interface WSAnomalyMessage {
  type: "anomaly_detected";
  symbol: string;
  anomaly_type: string;
  severity: AlertSeverity;
  description: string;
}

export interface WSPortfolioMessage {
  type: "portfolio_update";
  pnl: number;
  pnl_pct: number;
  positions: { symbol: string; pnl: number; pnl_pct: number }[];
}

export interface WSHeartbeatMessage {
  type: "heartbeat";
  server_time: string;
}

export type WSMessage =
  | WSTickMessage
  | WSPredictionMessage
  | WSAlertMessage
  | WSRegimeMessage
  | WSAnomalyMessage
  | WSPortfolioMessage
  | WSHeartbeatMessage;

// ─── UI Types ────────────────────────────────────────────────

export interface NavItem {
  label: string;
  href: string;
  icon: string;
  badge?: number;
}

export interface StatCard {
  label: string;
  value: string;
  change: number;
  changeLabel: string;
  icon: string;
}

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";
