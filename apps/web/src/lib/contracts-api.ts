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
    win_rate: number;
    profit_factor: number;
    num_trades: number;
  };
  equity_curve: Array<{ date: string; portfolio_value: number; benchmark_value: number }>;
  drawdown_series: Array<{ date: string; drawdown_pct: number }>;
  walk_forward?: { fold_sharpes: number[] };
}

export interface BacktestRunRequest {
  strategy_name: string;
  symbols?: string[];
  symbol?: string;
  start_date?: string;
  end_date?: string;
  benchmark?: string;
  initial_capital?: number;
  commission_pct?: number;
  slippage_pct?: number;
  parameters?: Record<string, unknown>;
}

export interface BacktestRunResponse {
  job_id: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "SUCCESS" | "DONE";
  estimated_seconds?: number;
  strategy_name: string;
}

export interface BacktestStatusResponse {
  job_id: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "SUCCESS" | "DONE";
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

export interface JournalEntry {
  id: string;
  symbol: string;
  notes: string;
  tags?: string | null;
  rating?: number | null;
  entry_price?: number | null;
  exit_price?: number | null;
  quantity?: number | null;
  direction?: string | null;
  created_at: string;
}

import { getApiV1Url } from "@/lib/runtime-config";

const API_URL = getApiV1Url();
type UnknownRecord = Record<string, unknown>;

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : fallback;
  }
  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }
  return fallback;
}

function toState(value: unknown): "BULL" | "BEAR" | "SIDEWAYS" | "CRISIS" {
  const normalized = String(value ?? "").trim().toUpperCase();
  if (
    normalized === "BULL" ||
    normalized === "BEAR" ||
    normalized === "SIDEWAYS" ||
    normalized === "CRISIS"
  ) {
    return normalized;
  }
  return "SIDEWAYS";
}

function normalizeRegimeProbabilities(value: unknown): Record<string, number> {
  if (Array.isArray(value)) {
    return {
      BULL: toNumber(value[0]),
      BEAR: toNumber(value[1]),
      SIDEWAYS: toNumber(value[2]),
      CRISIS: toNumber(value[3]),
    };
  }

  const source = value && typeof value === "object" ? (value as UnknownRecord) : {};
  return {
    BULL: toNumber(source.BULL ?? source.bull),
    BEAR: toNumber(source.BEAR ?? source.bear),
    SIDEWAYS: toNumber(source.SIDEWAYS ?? source.sideways),
    CRISIS: toNumber(source.CRISIS ?? source.crisis),
  };
}

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

async function postJsonWithHeaders<TResponse, TBody>(
  path: string,
  body: TBody,
  headers: Record<string, string>,
): Promise<TResponse> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...headers,
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
    return getJson<{ indices?: MarketIndex[] } | MarketIndex[]>("/market/indices").then((raw) => {
      const arr = Array.isArray(raw) ? raw : (raw?.indices || []);
      return arr.map((item) => ({
        name: String(item.name ?? ""),
        ticker: String(item.ticker ?? ""),
        value: toNumber(item.value),
        change: toNumber(item.change),
        change_pct: toNumber(item.change_pct),
        regime_state: toState(item.regime_state) as MarketIndex["regime_state"],
      }));
    });
  },

  getMovers(exchange: "NSE" | "NYSE" | "CRYPTO" = "NSE", type: "gainers" | "losers" | "volume" | "momentum" = "momentum"): Promise<MarketMover[]> {
    return getJson<Record<string, unknown>>(`/market/movers?exchange=${exchange}&type=${type}`).then((raw) => {
      const assets = raw && Array.isArray(raw.assets) ? (raw.assets as Record<string, unknown>[]) : [];
      return assets.map((item) => ({
        ticker: String(item.ticker ?? ""),
        name: String(item.name ?? ""),
        exchange: String(item.exchange ?? ""),
        price: Number(item.price ?? 0),
        change_pct: Number(item.change_pct ?? item.change_percent ?? 0),
        volume: Number(item.volume ?? 0),
        signal_direction: (item.signal_direction ?? "NEUTRAL") as MarketMover["signal_direction"],
        confidence: Number(item.signal_confidence ?? item.confidence ?? 0.5),
      }));
    });
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
    const idempotencyKey = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `idem-${Date.now()}`;
    return postJsonWithHeaders<PaymentIntentResponse, PaymentIntentRequest>("/payments/intents", payload, {
      "Idempotency-Key": idempotencyKey,
    });
  },

  confirmPaymentIntent(payload: PaymentConfirmRequest): Promise<PaymentConfirmResponse> {
    return postJson<PaymentConfirmResponse, PaymentConfirmRequest>("/payments/confirm", payload);
  },

  getPaymentHistory(limit: number = 20): Promise<PaymentHistoryResponse> {
    return getJson<PaymentHistoryResponse>(`/payments/history?limit=${limit}`);
  },

  getModelAccuracy(): Promise<ModelAccuracyItem[]> {
    return getJson<UnknownRecord>("/monitor/model-accuracy").then((raw) => {
      const models = Array.isArray(raw.models) ? (raw.models as UnknownRecord[]) : [];
      const items = models.map((item) => ({
        model: String(item.model_name ?? "tft") as ModelAccuracyItem["model"],
        precision: toNumber(item.precision),
        recall: toNumber(item.recall),
        directional_accuracy: toNumber(item.directional_accuracy),
        p50_rmse: toNumber(item.p50_rmse),
        winkler_coverage_score: toNumber(item.winkler_coverage ?? item.winkler_coverage_score),
      }));

      const benchmarkAccuracy = toNumber(raw.benchmark_ensemble_accuracy, NaN);
      if (Number.isFinite(benchmarkAccuracy)) {
        items.push({
          model: "ensemble",
          precision: benchmarkAccuracy,
          recall: benchmarkAccuracy,
          directional_accuracy: benchmarkAccuracy,
          p50_rmse: items[0]?.p50_rmse ?? 0,
          winkler_coverage_score: items[0]?.winkler_coverage_score ?? 0,
        });
      }

      return items;
    });
  },

  getDrift(): Promise<DriftItem[]> {
    return getJson<UnknownRecord>("/monitor/drift").then((raw) => {
      const models = Array.isArray(raw.models) ? (raw.models as UnknownRecord[]) : [];
      return models.map((item) => {
        const residuals =
          item.residual_distribution_now && typeof item.residual_distribution_now === "object"
            ? (item.residual_distribution_now as UnknownRecord)
            : {};

        return {
          model: String(item.model_name ?? "tft") as DriftItem["model"],
          adwin_p_value: toNumber(item.adwin_p_value),
          drift_detected: Boolean(item.drift_detected),
          residual_distribution: [
            toNumber(residuals.min),
            toNumber(residuals.p25),
            toNumber(residuals.mean),
            toNumber(residuals.p50),
            toNumber(residuals.p75),
            toNumber(residuals.max),
          ],
          ks_stat: toNumber(item.ks_statistic ?? item.ks_stat),
        };
      });
    });
  },

  getEnsembleWeightHistory(days: number = 252): Promise<EnsembleWeightPoint[]> {
    return getJson<UnknownRecord>(`/monitor/ensemble-weights-history?days=${days}`).then((raw) => {
      const data = Array.isArray(raw.data) ? (raw.data as UnknownRecord[]) : [];
      return data.map((item) => ({
        date: String(item.date ?? new Date().toISOString()),
        tft: toNumber(item.tft),
        hmm_garch: toNumber(item.hmm_garch),
        gnn: toNumber(item.gnn),
        lstm_attn: toNumber(item.lstm_attn),
        xgboost: toNumber(item.xgboost),
      }));
    });
  },

  optimizePortfolio(payload: PortfolioOptimizeRequest): Promise<PortfolioOptimizeResponse> {
    return postJson<PortfolioOptimizeResponse, PortfolioOptimizeRequest>("/portfolio/optimize", payload);
  },

  getBacktestResults(jobId: string): Promise<BacktestResultsResponse> {
    return getJson<BacktestResultsResponse>(`/backtest/results/${encodeURIComponent(jobId)}`);
  },

  runBacktest(payload: BacktestRunRequest): Promise<BacktestRunResponse> {
    const symbols = payload.symbols || (payload.symbol ? [payload.symbol] : []);
    const backendPayload = {
      strategy_name: payload.strategy_name === "macd_crossover" ? "ma_crossover" : (payload.strategy_name === "rsi_mean_reversion" ? "rsi_mrv" : payload.strategy_name),
      strategy_params: {
        commission_pct: payload.commission_pct ?? 0.001,
        slippage_pct: payload.slippage_pct ?? 0.0005,
        benchmark: payload.benchmark ?? "^NSEI",
        ...(payload.parameters || {}),
      },
      universe: symbols.length > 0 ? symbols : ["RELIANCE.NS"],
      date_from: payload.start_date || new Date(Date.now() - 365*24*60*60*1000).toISOString().split('T')[0],
      date_to: payload.end_date || new Date().toISOString().split('T')[0],
      initial_capital: payload.initial_capital ?? 1000000,
    };
    return postJson<BacktestRunResponse, typeof backendPayload>("/backtest/run", backendPayload);
  },

  getBacktestStatus(jobId: string): Promise<BacktestStatusResponse> {
    return getJson<BacktestStatusResponse>(`/backtest/status/${encodeURIComponent(jobId)}`);
  },

  getRegimeCurrent(): Promise<RegimeCurrentResponse> {
    return getJson<UnknownRecord>("/regime/current").then((raw) => ({
      state: toState(raw.state),
      probs: normalizeRegimeProbabilities(raw.probs),
      transition_matrix: Array.isArray(raw.transition_matrix)
        ? raw.transition_matrix.map((row) =>
            Array.isArray(row) ? row.map((value) => toNumber(value)) : []
          )
        : [],
      cond_vol_1d: toNumber(raw.cond_vol_1d),
      cond_vol_5d: toNumber(raw.cond_vol_5d),
      cond_vol_21d: toNumber(raw.cond_vol_21d),
      days_in_state: toNumber(raw.days_in_state),
      last_transition_date: String(raw.last_transition_date ?? ""),
    }));
  },

  getRegimeHistory(days: number = 252): Promise<RegimeHistoryPoint[]> {
    return getJson<UnknownRecord>(`/regime/history?days=${days}`).then((raw) => {
      const data = Array.isArray(raw.data) ? (raw.data as UnknownRecord[]) : [];
      return data.map((item) => ({
        time: String(item.time ?? new Date().toISOString()),
        state: toState(item.state),
        probs: normalizeRegimeProbabilities(item.probs),
        cond_vol: toNumber(item.cond_vol),
      }));
    });
  },

  getRegimeStatistics(): Promise<RegimeStatisticsItem[]> {
    return getJson<UnknownRecord>("/regime/statistics").then((raw) => {
      const rows = Array.isArray(raw.statistics) ? (raw.statistics as UnknownRecord[]) : [];
      return rows.map((item) => ({
        state: toState(item.state),
        avg_duration: toNumber(item.avg_duration_days ?? item.avg_duration),
        avg_return: toNumber(item.avg_daily_return ?? item.avg_return),
        avg_vol: toNumber(item.avg_volatility ?? item.avg_vol),
        freq: toNumber(item.frequency_pct ?? item.freq) / 100,
      }));
    });
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

  getJournals(): Promise<JournalEntry[]> {
    return getJson<JournalEntry[]>("/journal");
  },

  createJournal(payload: Partial<JournalEntry>): Promise<JournalEntry> {
    return postJson<JournalEntry, Partial<JournalEntry>>("/journal", payload);
  },

  deleteJournal(id: string): Promise<boolean> {
    return fetch(`${API_URL}/journal/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }).then((res) => {
      if (!res.ok) throw new Error("Failed to delete journal entry");
      return true;
    });
  },
};
