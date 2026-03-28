export interface MarketIndex {
  name: string;
  ticker: string;
  value: number;
  change: number;
  change_pct: number;
  regime_state: "BULL" | "BEAR" | "SIDEWAYS" | "CRISIS";
}

export interface MarketMover {
  ticker: string;
  name: string;
  exchange: string;
  price: number;
  change_pct: number;
  volume: number;
  signal_direction: "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL";
  confidence: number;
}

export interface PortfolioHolding {
  symbol: string;
  quantity: number;
  avg_buy_price: number;
  ltp: number;
  unrealized_pnl: number;
}

export interface PortfolioHoldingsResponse {
  holdings: PortfolioHolding[];
  total_unrealized_pnl: number;
}

export interface PortfolioPerformancePoint {
  date: string;
  portfolio_value: number;
  benchmark_value: number;
}

export interface PortfolioPerformanceResponse {
  series: PortfolioPerformancePoint[];
  total_return: number;
  benchmark_return: number;
}

export interface PortfolioRiskMetrics {
  sharpe: number;
  sortino: number;
  beta: number;
  alpha: number;
  var_95: number;
  cvar_95: number;
}

export interface PaymentMethod {
  code: "UPI" | "CARD" | "NETBANKING";
  label: string;
  enabled: boolean;
  min_amount: number;
  max_amount: number;
}

export interface PaymentMethodsResponse {
  methods: PaymentMethod[];
  generated_at: string;
}

export interface PaymentIntentRequest {
  amount: number;
  currency?: "INR";
  method: "UPI" | "CARD" | "NETBANKING";
  description?: string;
}

export interface PaymentIntentResponse {
  intent_id: string;
  provider_ref: string;
  amount: number;
  currency: string;
  method: string;
  status: "requires_confirmation" | "confirmed" | "failed";
  created_at: string;
}

export interface PaymentConfirmRequest {
  intent_id: string;
  confirmation_code: string;
}

export interface PaymentConfirmResponse {
  payment_id: string;
  intent_id: string;
  status: "succeeded" | "failed";
  credited_amount: number;
  wallet_balance: number;
  completed_at: string;
}

export interface WalletBalanceResponse {
  currency: string;
  wallet_balance: number;
  updated_at: string;
}

export interface PaymentHistoryItem {
  payment_id: string;
  intent_id: string;
  amount: number;
  currency: string;
  method: string;
  status: string;
  created_at: string;
  completed_at?: string | null;
}

export interface PaymentHistoryResponse {
  items: PaymentHistoryItem[];
  total: number;
  limit: number;
}

export interface PortfolioTransactionRequest {
  symbol: string;
  type: "BUY" | "SELL";
  quantity: number;
  price: number;
  brokerage?: number;
  stt?: number;
}

export interface PortfolioTransactionResponse {
  transaction_id: string;
  symbol: string;
  type: "BUY" | "SELL";
  quantity: number;
  price: number;
  net_amount: number;
  timestamp: string;
  portfolio_updated: boolean;
}

export interface ModelAccuracyItem {
  model: "tft" | "hmm_garch" | "gnn" | "lstm_attn" | "xgboost" | "ensemble";
  precision: number;
  recall: number;
  directional_accuracy: number;
  p50_rmse: number;
  winkler_coverage_score: number;
}

export interface DriftItem {
  model: "tft" | "hmm_garch" | "gnn" | "lstm_attn" | "xgboost" | "ensemble";
  adwin_p_value: number;
  drift_detected: boolean;
  residual_distribution: number[];
  ks_stat: number;
}

export interface EnsembleWeightPoint {
  date: string;
  tft: number;
  hmm_garch: number;
  gnn: number;
  lstm_attn: number;
  xgboost: number;
}

export interface PortfolioOptimizeRequest {
  universe: string[];
  method: "hrp" | "black_litterman" | "cvar" | "mean_variance";
  constraints: {
    max_weight: number;
    max_turnover?: number;
  };
  use_ml_views: boolean;
}

export interface PortfolioOptimizeResponse {
  weights: Record<string, number>;
  expected_return: number;
  expected_vol: number;
  sharpe_ratio: number;
  efficient_frontier: Array<{ return: number; vol: number }>;
}

export interface BacktestResultsResponse {
  job_id?: string;
  metrics: {
    total_return: number;
    cagr: number;
    sharpe: number;
    max_drawdown: number;
  };
  equity_curve: Array<{ date: string; portfolio_value: number; benchmark_value: number }>;
  drawdown_series: Array<{ date: string; drawdown_pct: number }>;
  walk_forward?: { fold_sharpes: number[] };
}

export interface BacktestRunRequest {
  strategy_name: "mean_reversion" | "momentum" | "volatility_breakout" | "ml_alpha" | "stat_arb";
  symbols: string[];
  start_date: string;
  end_date: string;
  benchmark: string;
  initial_capital: number;
  commission_pct: number;
  slippage_pct: number;
}

export interface BacktestRunResponse {
  job_id: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  estimated_seconds?: number;
  strategy_name: string;
}

export interface BacktestStatusResponse {
  job_id: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  progress_pct?: number;
  result_preview?: {
    sharpe?: number;
    max_drawdown?: number;
  };
}

export interface RegimeCurrentResponse {
  state: "BULL" | "BEAR" | "SIDEWAYS" | "CRISIS";
  probs: Record<string, number>;
  transition_matrix: number[][];
  cond_vol_1d: number;
  cond_vol_5d: number;
  cond_vol_21d: number;
  days_in_state: number;
  last_transition_date: string;
}

export interface RegimeHistoryPoint {
  time: string;
  state: "BULL" | "BEAR" | "SIDEWAYS" | "CRISIS";
  probs: Record<string, number>;
  cond_vol: number;
}

export interface RegimeStatisticsItem {
  state: "BULL" | "BEAR" | "SIDEWAYS" | "CRISIS";
  avg_duration: number;
  avg_return: number;
  avg_vol: number;
  freq: number;
}

export interface ExplainShapContribution {
  name: string;
  shap_val: number;
  feature_val: number;
  pct_rank: number;
}

export interface ExplainShapResponse {
  model: "xgboost";
  feature_contributions: ExplainShapContribution[];
  base_value: number;
  output_value: number;
  waterfall_ready: boolean;
}

export interface ExplainAttentionTopTimestep {
  date: string;
  weight: number;
}

export interface ExplainAttentionResponse {
  model: "tft" | "lstm_attn";
  weights: number[][];
  mean_weights: number[];
  top_timesteps: ExplainAttentionTopTimestep[];
}

export interface CounterfactualFeatureChange {
  name: string;
  original: number;
  counterfactual: number;
}

export interface CounterfactualResponse {
  cf_id: string;
  changed_features: CounterfactualFeatureChange[];
  resulting_signal: "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL";
  proximity_score: number;
}

export interface CounterfactualRequest {
  target_direction: "BUY" | "SELL";
  num_cfs: number;
}

export interface CorrelationGraphNode {
  ticker: string;
  sector: string;
  x: number;
  y: number;
  size: number;
}

export interface CorrelationGraphEdge {
  source: string;
  target: string;
  correlation: number;
}

export interface CorrelationGraphResponse {
  window_days: number;
  central_asset: string;
  nodes: CorrelationGraphNode[];
  edges: CorrelationGraphEdge[];
  top_correlates: Array<{ ticker: string; correlation: number }>;
}

export interface FactorExposureItem {
  factor: string;
  beta: number;
}

export interface FactorExposureResponse {
  symbol: string;
  window_days: number;
  exposures: FactorExposureItem[];
  metrics: Record<string, number>;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "GET",
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status}) for ${path}`);
  }
  return (await response.json()) as T;
}

async function postJson<TResponse, TBody>(path: string, body: TBody): Promise<TResponse> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status}) for ${path}`);
  }
  return (await response.json()) as TResponse;
}

export const contractsApi = {
  getIndices(): Promise<MarketIndex[]> {
    return getJson<MarketIndex[]>("/market/indices");
  },

  getMovers(exchange: "NSE" | "NYSE" | "CRYPTO" = "NSE", type: "gainers" | "losers" | "volume" | "momentum" = "momentum"): Promise<MarketMover[]> {
    return getJson<MarketMover[]>(`/market/movers?exchange=${exchange}&type=${type}`);
  },

  getPortfolioHoldings(): Promise<PortfolioHoldingsResponse> {
    return getJson<Record<string, unknown>>("/portfolio/holdings").then((raw) => {
      const rawHoldings = Array.isArray(raw.holdings) ? (raw.holdings as Record<string, unknown>[]) : [];
      return {
        holdings: rawHoldings.map((holding) => ({
          symbol: String(holding.symbol ?? ""),
          quantity: Number(holding.quantity ?? 0),
          avg_buy_price: Number(holding.avg_buy_price ?? holding.avg_price ?? 0),
          ltp: Number(holding.ltp ?? holding.current_price ?? 0),
          unrealized_pnl: Number(holding.unrealized_pnl ?? 0),
        })),
        total_unrealized_pnl: Number(raw.total_unrealized_pnl ?? 0),
      };
    });
  },

  getPortfolioPerformance(): Promise<PortfolioPerformanceResponse> {
    return getJson<Record<string, unknown>>("/portfolio/performance").then((raw) => {
      const rawSeries = Array.isArray(raw.series) ? (raw.series as Record<string, unknown>[]) : [];
      return {
        series: rawSeries.map((point) => ({
          date: String(point.date ?? new Date().toISOString()),
          portfolio_value: Number(point.portfolio_value ?? 0),
          benchmark_value: Number(point.benchmark_value ?? 0),
        })),
        total_return: Number(raw.total_return ?? 0),
        benchmark_return: Number(raw.benchmark_return ?? 0),
      };
    });
  },

  getPortfolioRiskMetrics(): Promise<PortfolioRiskMetrics> {
    return getJson<Record<string, unknown>>("/portfolio/risk-metrics").then((raw) => ({
      sharpe: Number(raw.sharpe ?? raw.sharpe_ratio ?? 0),
      sortino: Number(raw.sortino ?? raw.sortino_ratio ?? 0),
      beta: Number(raw.beta ?? 0),
      alpha: Number(raw.alpha ?? 0),
      var_95: Number(raw.var_95 ?? 0),
      cvar_95: Number(raw.cvar_95 ?? 0),
    }));
  },

  postPortfolioTransaction(payload: PortfolioTransactionRequest): Promise<PortfolioTransactionResponse> {
    return postJson<PortfolioTransactionResponse, PortfolioTransactionRequest>("/portfolio/transaction", payload);
  },

  getPaymentMethods(): Promise<PaymentMethodsResponse> {
    return getJson<PaymentMethodsResponse>("/payments/methods");
  },

  getWalletBalance(): Promise<WalletBalanceResponse> {
    return getJson<WalletBalanceResponse>("/payments/balance");
  },

  createPaymentIntent(payload: PaymentIntentRequest): Promise<PaymentIntentResponse> {
    return postJson<PaymentIntentResponse, PaymentIntentRequest>("/payments/intents", payload);
  },

  confirmPaymentIntent(payload: PaymentConfirmRequest): Promise<PaymentConfirmResponse> {
    return postJson<PaymentConfirmResponse, PaymentConfirmRequest>("/payments/confirm", payload);
  },

  getPaymentHistory(limit: number = 20): Promise<PaymentHistoryResponse> {
    return getJson<PaymentHistoryResponse>(`/payments/history?limit=${limit}`);
  },

  getModelAccuracy(): Promise<ModelAccuracyItem[]> {
    return getJson<ModelAccuracyItem[]>("/monitor/model-accuracy");
  },

  getDrift(): Promise<DriftItem[]> {
    return getJson<DriftItem[]>("/monitor/drift");
  },

  getEnsembleWeightHistory(days: number = 252): Promise<EnsembleWeightPoint[]> {
    return getJson<EnsembleWeightPoint[]>(`/monitor/ensemble-weights-history?days=${days}`);
  },

  optimizePortfolio(payload: PortfolioOptimizeRequest): Promise<PortfolioOptimizeResponse> {
    return postJson<PortfolioOptimizeResponse, PortfolioOptimizeRequest>("/portfolio/optimize", payload);
  },

  getBacktestResults(jobId: string): Promise<BacktestResultsResponse> {
    return getJson<BacktestResultsResponse>(`/backtest/results/${encodeURIComponent(jobId)}`);
  },

  runBacktest(payload: BacktestRunRequest): Promise<BacktestRunResponse> {
    return postJson<BacktestRunResponse, BacktestRunRequest>("/backtest/run", payload);
  },

  getBacktestStatus(jobId: string): Promise<BacktestStatusResponse> {
    return getJson<BacktestStatusResponse>(`/backtest/status/${encodeURIComponent(jobId)}`);
  },

  getRegimeCurrent(): Promise<RegimeCurrentResponse> {
    return getJson<RegimeCurrentResponse>("/regime/current");
  },

  getRegimeHistory(days: number = 252): Promise<RegimeHistoryPoint[]> {
    return getJson<RegimeHistoryPoint[]>(`/regime/history?days=${days}`);
  },

  getRegimeStatistics(): Promise<RegimeStatisticsItem[]> {
    return getJson<RegimeStatisticsItem[]>("/regime/statistics");
  },

  getExplainShap(symbol: string): Promise<ExplainShapResponse> {
    return getJson<ExplainShapResponse>(`/explain/shap/${encodeURIComponent(symbol)}`);
  },

  getExplainAttention(symbol: string, model: "tft" | "lstm_attn" = "tft"): Promise<ExplainAttentionResponse> {
    return getJson<ExplainAttentionResponse>(`/explain/attention/${encodeURIComponent(symbol)}?model=${model}`);
  },

  getCounterfactuals(symbol: string, payload: CounterfactualRequest): Promise<CounterfactualResponse[]> {
    return postJson<CounterfactualResponse[], CounterfactualRequest>(`/explain/counterfactual/${encodeURIComponent(symbol)}`, payload);
  },

  getCorrelationGraph(windowDays: number = 60): Promise<CorrelationGraphResponse> {
    return getJson<CorrelationGraphResponse>(`/research/correlation-graph?window_days=${windowDays}`);
  },

  getFactorExposure(symbol: string = "RELIANCE.NS", windowDays: number = 126): Promise<FactorExposureResponse> {
    return getJson<FactorExposureResponse>(`/research/factor-exposure?symbol=${encodeURIComponent(symbol)}&window_days=${windowDays}`);
  },
};
