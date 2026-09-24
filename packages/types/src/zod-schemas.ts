import { makeApi, Zodios, type ZodiosOptions } from "@zodios/core";
import { z } from "zod";

type AttentionResponse = {
  symbol: string;
  model: string;
  weights: Array<Array<string>>;
  mean_weights: Array<string>;
  top_timesteps: Array<AttentionTimestep>;
  num_heads: number;
  num_timesteps: number;
  timestamp: string;
};
type AttentionTimestep = {
  date: string;
  weight: string;
};
type BacktestRequest = {
  strategy_name: string;
  strategy_params?: {} | undefined;
  universe: Array<string>;
  date_from: string;
  date_to: string;
  initial_capital: (number | string) | Array<number | string>;
  walk_forward?:
    | ((WalkForwardConfig | null) | Array<WalkForwardConfig | null>)
    | undefined;
  monte_carlo?:
    | ((MonteCarloConfig | null) | Array<MonteCarloConfig | null>)
    | undefined;
};
type WalkForwardConfig = Partial<{
  enabled: boolean;
  n_splits: number;
  purge_days: number;
  embargo_days: number;
}>;
type MonteCarloConfig = Partial<{
  enabled: boolean;
  n_simulations: number;
}>;
type BacktestResultsResponse = {
  job_id: string;
  strategy_name: string;
  universe: Array<string>;
  date_from: string;
  date_to: string;
  initial_capital: string;
  metrics: BacktestMetrics;
  equity_curve: Array<EquityCurvePoint>;
  drawdown_series: Array<DrawdownPoint>;
  trade_log: Array<TradeLogEntry>;
  walk_forward?:
    | ((WalkForwardMetrics | null) | Array<WalkForwardMetrics | null>)
    | undefined;
  monte_carlo?:
    | ((MonteCarloResults | null) | Array<MonteCarloResults | null>)
    | undefined;
  statistical_tests?:
    | ((StatisticalTests | null) | Array<StatisticalTests | null>)
    | undefined;
  status?: string | undefined;
  completed_at: string;
  excluded_tickers?: ((Array<{}> | null) | Array<Array<{}> | null>) | undefined;
};
type BacktestMetrics = {
  total_return: string;
  cagr: string;
  sharpe: string;
  sharpe_ratio: string;
  sortino_ratio: string;
  calmar_ratio: string;
  omega_ratio: string;
  max_drawdown: string;
  max_drawdown_duration_days: number;
  win_rate: string;
  profit_factor: string;
  avg_win: string;
  avg_loss: string;
  payoff_ratio: string;
  num_trades: number;
  gross_profit: string;
  gross_loss: string;
  tail_ratio: string;
  serenity_ratio: string;
  deflated_sharpe: string;
};
type EquityCurvePoint = {
  date: string;
  portfolio_value: string;
  benchmark_value?: ((string | null) | Array<string | null>) | undefined;
};
type DrawdownPoint = {
  date: string;
  drawdown_pct: string;
};
type TradeLogEntry = {
  date: string;
  symbol: string;
  direction: string;
  quantity: string;
  price: string;
  pnl: string;
  cum_pnl: string;
  commission: string;
};
type WalkForwardMetrics = {
  fold_sharpes: Array<string>;
  mean_sharpe: string;
  std_sharpe: string;
  t_statistic: string;
  p_value: string;
};
type MonteCarloResults = {
  percentiles: {};
  prob_of_ruin_10pct: string;
  prob_of_ruin_25pct: string;
  fan_paths_sample: Array<Array<string>>;
};
type StatisticalTests = {
  dm_test_statistic: string;
  dm_test_p_value: string;
  dm_test_vs_benchmark?: string | undefined;
  sharpe_se: string;
  min_backtest_length_days: number;
  multiple_testing_correction?: string | undefined;
};
type CorrelationGraphResponse = {
  window_days: number;
  central_asset: string;
  nodes: Array<CorrelationNode>;
  edges: Array<CorrelationEdge>;
  top_correlates: Array<{}>;
};
type CorrelationNode = {
  ticker: string;
  sector: string;
  x: number;
  y: number;
  size: number;
};
type CorrelationEdge = {
  source: string;
  target: string;
  correlation: number;
};
type CounterfactualInstance = {
  cf_id: string;
  changed_features: Array<FeatureChange>;
  resulting_signal: string;
  resulting_confidence: string;
  proximity_score: string;
};
type FeatureChange = {
  name: string;
  original_value: string;
  counterfactual_value: string;
  change_pct: string;
};
type DriftResponse = {
  models: Array<ModelDriftMetrics>;
  overall_drift_detected: boolean;
  generated_at: string;
};
type ModelDriftMetrics = {
  model_name: string;
  adwin_p_value: string;
  drift_detected: boolean;
  ks_statistic: string;
  ks_p_value: string;
  residual_distribution_now: DriftDistribution;
  residual_distribution_baseline: DriftDistribution;
  days_since_retrain: number;
  last_retraining_date: string;
  as_of_date: string;
};
type DriftDistribution = {
  mean: string;
  std: string;
  p25: string;
  p50: string;
  p75: string;
  min: string;
  max: string;
};
type EconomicCalendarResponse = {
  events: Array<EconomicEvent>;
  period_start: string;
  period_end: string;
};
type EconomicEvent = {
  date: string;
  event_name: string;
  country: string;
  importance: string;
  forecast?: ((string | null) | Array<string | null>) | undefined;
  previous?: ((string | null) | Array<string | null>) | undefined;
};
type ExplainAttentionResponse = {
  model: "tft" | "lstm_attn";
  weights: Array<Array<number>>;
  mean_weights: Array<number>;
  top_timesteps: Array<AttentionTopTimestep>;
};
type AttentionTopTimestep = {
  date: string;
  weight: number;
};
type ExplainShapResponse = {
  model: string;
  feature_contributions: Array<app__schemas__intelligence__SHAPContribution>;
  base_value: number;
  output_value: number;
  waterfall_ready: boolean;
};
type app__schemas__intelligence__SHAPContribution = {
  name: string;
  shap_val: number;
  feature_val: number;
  pct_rank: number;
};
type FactorExposureResponse = {
  symbol: string;
  window_days: number;
  exposures: Array<FactorExposureItem>;
  metrics: {};
};
type FactorExposureItem = {
  factor: string;
  beta: number;
};
type HTTPValidationError = Partial<{
  detail: Array<ValidationError>;
}>;
type ValidationError = {
  loc: Array<(string | number) | Array<string | number>>;
  msg: string;
  type: string;
  input?: unknown | undefined;
  ctx?: {} | undefined;
};
type HeatmapResponse = {
  exchange: string;
  metric: string;
  sectors: {};
  generated_at: string;
};
type SectorNode = {
  ticker: string;
  name: string;
  value: string;
  metric_value: string;
  exchange: string;
};
type HistoryResponse = {
  symbol: string;
  interval: string;
  bars: Array<OHLCVBar>;
  data_freshness_seconds?: ((number | null) | Array<number | null>) | undefined;
  source?: string | undefined;
};
type OHLCVBar = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};
type HoldingsResponse = {
  holdings: Array<HoldingData>;
  total_invested: string;
  total_current_value: string;
  total_unrealized_pnl: string;
  total_unrealized_pnl_pct: string;
  cash_balance: string;
  portfolio_value: string;
  timestamp: string;
};
type HoldingData = {
  symbol: string;
  quantity: string;
  avg_price: string;
  current_price: string;
  unrealized_pnl: string;
  unrealized_pnl_pct: string;
  in_position_days: number;
};
type IndicesResponse = {
  indices: Array<IndexData>;
};
type IndexData = {
  name: string;
  ticker: string;
  value: string;
  change: string;
  change_pct: string;
  regime_state: string;
  timestamp: string;
};
type ModelAccuracyResponse = {
  models: Array<ModelAccuracyMetrics>;
  benchmark_ensemble_accuracy: string;
  generated_at: string;
};
type ModelAccuracyMetrics = {
  model_name: string;
  period_days?: number | undefined;
  precision: string;
  recall: string;
  f1_score: string;
  directional_accuracy: string;
  p50_rmse: string;
  winkler_coverage: string;
  as_of_date: string;
};
type MoversResponse = {
  assets: Array<MoverData>;
  exchange: string;
  type: string;
  generated_at: string;
};
type MoverData = {
  ticker: string;
  name: string;
  exchange: string;
  price: string;
  change_pct: string;
  volume: string;
  signal_direction: string;
  signal_confidence: number;
  rank: number;
};
type OptimizationRequest = {
  universe: Array<string>;
  method: string;
  constraints?:
    | ((OptimizationConstraints | null) | Array<OptimizationConstraints | null>)
    | undefined;
  use_ml_views?: boolean | undefined;
};
type OptimizationConstraints = Partial<{
  max_weight: (number | string) | Array<number | string>;
  min_weight: (number | string) | Array<number | string>;
  sector_limits: ({} | null) | Array<{} | null>;
  max_turnover: (number | string | null) | Array<number | string | null>;
  leverage_limit: (number | string) | Array<number | string>;
}>;
type OptimizationResponse = {
  method: string;
  weights: Array<OptimizedWeight>;
  expected_return: string;
  expected_volatility: string;
  sharpe_ratio: string;
  efficient_frontier?:
    | (
        | (Array<EfficientFrontierPoint> | null)
        | Array<Array<EfficientFrontierPoint> | null>
      )
    | undefined;
  hrp_dendrogram?: (({} | null) | Array<{} | null>) | undefined;
  bl_posterior_returns?: (({} | null) | Array<{} | null>) | undefined;
  excluded_tickers?: ((Array<{}> | null) | Array<Array<{}> | null>) | undefined;
  timestamp: string;
};
type OptimizedWeight = {
  symbol: string;
  weight: string;
};
type EfficientFrontierPoint = {
  expected_return: string;
  expected_volatility: string;
  sharpe_ratio: string;
  weights: {};
};
type PerformanceResponse = {
  series: Array<PerformancePoint>;
  start_date: string;
  end_date: string;
  total_return: string;
  benchmark_return: string;
  excess_return: string;
};
type PerformancePoint = {
  date: string;
  portfolio_value: string;
  benchmark_value: string;
  daily_return: string;
  benchmark_return: string;
};
type QuoteResponse = {
  ticker: string;
  name: string;
  price: string;
  change: string;
  change_pct: string;
  volume: string;
  market_cap?: ((string | null) | Array<string | null>) | undefined;
  pe_ratio?: ((string | null) | Array<string | null>) | undefined;
  week_52_high?: ((string | null) | Array<string | null>) | undefined;
  week_52_low?: ((string | null) | Array<string | null>) | undefined;
  regime?: ((RegimeData | null) | Array<RegimeData | null>) | undefined;
  signal?: ((SignalData | null) | Array<SignalData | null>) | undefined;
  timestamp: string;
  data_freshness_seconds?: ((number | null) | Array<number | null>) | undefined;
  source?: string | undefined;
};
type RegimeData = {
  state: string;
  probs: Array<number>;
};
type SignalData = {
  direction: string;
  confidence: number;
};
type RegimeHistoryResponse = {
  period_days: number;
  start_date: string;
  end_date: string;
  data: Array<app__schemas__regime__RegimeHistoryPoint>;
  transitions: number;
};
type app__schemas__regime__RegimeHistoryPoint = {
  time: string;
  state: string;
  state_index: number;
  probs: Array<string>;
  cond_vol: string;
  cond_vol_5d?: ((string | null) | Array<string | null>) | undefined;
  cond_vol_21d?: ((string | null) | Array<string | null>) | undefined;
};
type RegimeStatisticsResponse = {
  period_days: number;
  statistics: Array<RegimeStatistics>;
  most_common_state: string;
  mean_duration_all_states: string;
};
type RegimeStatistics = {
  state: string;
  state_index: number;
  avg_duration_days: string;
  frequency_pct: string;
  avg_daily_return: string;
  avg_volatility: string;
  min_volatility: string;
  max_volatility: string;
  best_daily_return: string;
  worst_daily_return: string;
};
type SHAPResponse = {
  symbol: string;
  model: string;
  feature_contributions: Array<app__schemas__explain__SHAPContribution>;
  base_value: string;
  output_value: string;
  waterfall_ready?: boolean | undefined;
  timestamp: string;
};
type app__schemas__explain__SHAPContribution = {
  name: string;
  shap_value: string;
  feature_value: string;
  percentile_rank: string;
};
type ScreenerPresetsResponse = {
  presets: Array<ScreenerPreset>;
};
type ScreenerPreset = {
  name: string;
  description: string;
  filters_json: {};
  created_at: string;
};
type ScreenerRunRequest = {
  exchange: Array<string>;
  filters: ScreenerFilterConfig;
  sort_by?: string | undefined;
  limit?: number | undefined;
};
type ScreenerFilterConfig = Partial<{
  asset_class: (string | null) | Array<string | null>;
  exchange:
    | (Array<string> | string | null)
    | Array<Array<string> | string | null>;
  market_cap_min: (number | string | null) | Array<number | string | null>;
  market_cap_max: (number | string | null) | Array<number | string | null>;
  pe_ratio_max: (number | string | null) | Array<number | string | null>;
  rsi_min: (number | string | null) | Array<number | string | null>;
  rsi_max: (number | string | null) | Array<number | string | null>;
  momentum_21d_min: (number | string | null) | Array<number | string | null>;
  volume_ratio_min: (number | string | null) | Array<number | string | null>;
  signal_direction:
    | (Array<string> | string | null)
    | Array<Array<string> | string | null>;
  regime_compatible: boolean;
  min_market_cap: (number | string | null) | Array<number | string | null>;
  max_market_cap: (number | string | null) | Array<number | string | null>;
  above_sma_200: (boolean | null) | Array<boolean | null>;
  volume_surge: (boolean | null) | Array<boolean | null>;
  ml_confidence_min: (number | string | null) | Array<number | string | null>;
}>;
type ScreenerRunResponse = {
  results: Array<ScreenerResult>;
  total_matched: number;
  filters_applied: {};
  generated_at: string;
};
type ScreenerResult = {
  ticker: string;
  name: string;
  exchange: string;
  asset_type: string;
  price: string;
  change_pct: string;
  pe_ratio?: ((string | null) | Array<string | null>) | undefined;
  rsi?: ((string | null) | Array<string | null>) | undefined;
  signal_direction: string;
  signal_confidence: string;
  regime_state: string;
  momentum_21d: string;
  volume_ratio: string;
};
type SearchResponse = {
  query: string;
  results: Array<SearchResult>;
  total_matched: number;
};
type SearchResult = {
  ticker: string;
  name: string;
  exchange: string;
  asset_type: string;
};
type UniverseResponse = {
  instruments: Array<InstrumentInfo>;
  min_price?: ((number | null) | Array<number | null>) | undefined;
  max_price?: ((number | null) | Array<number | null>) | undefined;
  rsi_min?: ((number | null) | Array<number | null>) | undefined;
  rsi_max?: ((number | null) | Array<number | null>) | undefined;
  above_sma_200?: ((boolean | null) | Array<boolean | null>) | undefined;
  volume_surge?: ((boolean | null) | Array<boolean | null>) | undefined;
  ml_confidence_min?: ((number | null) | Array<number | null>) | undefined;
  sort_by?: string | undefined;
  sort_order?: string | undefined;
  limit?: number | undefined;
  offset?: number | undefined;
};
type InstrumentInfo = {
  symbol: string;
  displayName: string;
  exchange: string;
  yfinanceTicker: string;
};
type WeightsHistoryResponse = {
  period_days?: number | undefined;
  data: Array<app__schemas__monitor__EnsembleWeightPoint>;
  start_date: string;
  end_date: string;
};
type app__schemas__monitor__EnsembleWeightPoint = {
  date: string;
  tft: string;
  hmm_garch: string;
  gnn: string;
  lstm_attn: string;
  xgboost: string;
};
type app__schemas__explain__CounterfactualResponse = {
  symbol: string;
  target_direction: string;
  counterfactuals: Array<CounterfactualInstance>;
  original_signal: string;
  original_confidence: string;
  timestamp: string;
};
type app__schemas__intelligence__CounterfactualResponse = {
  cf_id: string;
  changed_features: Array<CounterfactualFeatureChange>;
  resulting_signal: "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL";
  proximity_score: number;
};
type CounterfactualFeatureChange = {
  name: string;
  original: number;
  counterfactual: number;
};

const AuthRegister = z
  .object({
    email: z.string().email(),
    password: z.string(),
    full_name: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const ValidationError: z.ZodType<ValidationError> = z
  .object({
    loc: z.array(z.union([z.string(), z.number()])),
    msg: z.string(),
    type: z.string(),
    input: z.unknown().optional(),
    ctx: z.object({}).partial().passthrough().optional(),
  })
  .passthrough();
const HTTPValidationError: z.ZodType<HTTPValidationError> = z
  .object({ detail: z.array(ValidationError) })
  .partial()
  .passthrough();
const AuthLogin = z
  .object({ email: z.string().email(), password: z.string() })
  .passthrough();
const TokenResponse = z
  .object({
    access_token: z.string(),
    refresh_token: z.union([z.string(), z.null()]).optional(),
    token_type: z.string().optional().default("bearer"),
    expires_in: z.number().int().optional().default(3600),
  })
  .passthrough();
const AuthRefresh = z.object({ refresh_token: z.string() }).passthrough();
const UserProfileResponse = z
  .object({
    id: z.string(),
    email: z.string(),
    full_name: z.union([z.string(), z.null()]),
    status: z.string(),
  })
  .passthrough();
const UpdateProfileRequest = z
  .object({ full_name: z.string().min(1).max(120) })
  .passthrough();
const OrganizationResponse = z
  .object({
    id: z.string(),
    name: z.string(),
    slug: z.string(),
    role: z.string(),
  })
  .passthrough();
const MemberResponse = z
  .object({
    id: z.string(),
    user_id: z.string(),
    email: z.string(),
    full_name: z.union([z.string(), z.null()]),
    role: z.string(),
    status: z.string(),
  })
  .passthrough();
const InviteRequest = z
  .object({
    email: z.string().email(),
    role: z.string().optional().default("VIEWER"),
  })
  .passthrough();
const ApiKeyCreate = z
  .object({ name: z.string(), scopes: z.string() })
  .passthrough();
const BlogPostCreate = z
  .object({
    slug: z.string().min(3).max(180),
    title: z.string().min(3).max(220),
    excerpt: z.string().min(8).max(400),
    content: z.string().min(20),
    status: z.enum(["draft", "published"]).optional().default("draft"),
  })
  .passthrough();
const BlogPostUpdate = z
  .object({
    title: z.union([z.string(), z.null()]),
    excerpt: z.union([z.string(), z.null()]),
    content: z.union([z.string(), z.null()]),
    status: z.union([z.enum(["draft", "published"]), z.null()]),
  })
  .partial()
  .passthrough();
const NotificationCreate = z
  .object({
    user_id: z.string(),
    title: z.string().min(3).max(180),
    message: z.string().min(3),
    level: z
      .string()
      .regex(/^(info|success|warning|error)$/)
      .optional()
      .default("info"),
  })
  .passthrough();
const SubscriptionResponse = z
  .object({
    id: z.string(),
    status: z.string(),
    plan_name: z.string(),
    current_period_end: z.union([z.string(), z.null()]),
  })
  .passthrough();
const WatchlistResponse = z
  .object({
    symbols: z.array(z.string()),
    list_id: z.number().int().optional().default(0),
  })
  .passthrough();
const WatchlistAddRequest = z
  .object({
    symbol: z.string(),
    list_id: z.number().int().optional().default(0),
  })
  .passthrough();
const AlertCreate = z
  .object({ symbol: z.string(), alert_type: z.string(), threshold: z.number() })
  .passthrough();
const RegimeData: z.ZodType<RegimeData> = z
  .object({ state: z.string(), probs: z.array(z.number()) })
  .passthrough();
const SignalData: z.ZodType<SignalData> = z
  .object({ direction: z.string(), confidence: z.number().gte(0).lte(1) })
  .passthrough();
const QuoteResponse: z.ZodType<QuoteResponse> = z
  .object({
    ticker: z.string(),
    name: z.string(),
    price: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    change: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    change_pct: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    volume: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    market_cap: z.union([z.string(), z.null()]).optional(),
    pe_ratio: z.union([z.string(), z.null()]).optional(),
    week_52_high: z.union([z.string(), z.null()]).optional(),
    week_52_low: z.union([z.string(), z.null()]).optional(),
    regime: z.union([RegimeData, z.null()]).optional(),
    signal: z.union([SignalData, z.null()]).optional(),
    timestamp: z.string().datetime({ offset: true }),
    data_freshness_seconds: z.union([z.number(), z.null()]).optional(),
    source: z.string().optional().default("realtime"),
  })
  .passthrough();
const period = z.union([z.string(), z.null()]).optional();
const OHLCVBar: z.ZodType<OHLCVBar> = z
  .object({
    time: z.number().int(),
    open: z.number(),
    high: z.number(),
    low: z.number(),
    close: z.number(),
    volume: z.number(),
  })
  .passthrough();
const HistoryResponse: z.ZodType<HistoryResponse> = z
  .object({
    symbol: z.string(),
    interval: z.string(),
    bars: z.array(OHLCVBar),
    data_freshness_seconds: z.union([z.number(), z.null()]).optional(),
    source: z.string().optional().default("realtime"),
  })
  .passthrough();
const IndexData: z.ZodType<IndexData> = z
  .object({
    name: z.string(),
    ticker: z.string(),
    value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    change: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    change_pct: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    regime_state: z.string(),
    timestamp: z.string().datetime({ offset: true }),
  })
  .passthrough();
const IndicesResponse: z.ZodType<IndicesResponse> = z
  .object({ indices: z.array(IndexData) })
  .passthrough();
const MoverData: z.ZodType<MoverData> = z
  .object({
    ticker: z.string(),
    name: z.string(),
    exchange: z.string(),
    price: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    change_pct: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    volume: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    signal_direction: z.string(),
    signal_confidence: z.number(),
    rank: z.number().int(),
  })
  .passthrough();
const MoversResponse: z.ZodType<MoversResponse> = z
  .object({
    assets: z.array(MoverData),
    exchange: z.string(),
    type: z.string(),
    generated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const SectorNode: z.ZodType<SectorNode> = z
  .object({
    ticker: z.string(),
    name: z.string(),
    value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    metric_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    exchange: z.string(),
  })
  .passthrough();
const HeatmapResponse: z.ZodType<HeatmapResponse> = z
  .object({
    exchange: z.string(),
    metric: z.string(),
    sectors: z.record(z.array(SectorNode)),
    generated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const SearchResult: z.ZodType<SearchResult> = z
  .object({
    ticker: z.string(),
    name: z.string(),
    exchange: z.string(),
    asset_type: z.string(),
  })
  .passthrough();
const SearchResponse: z.ZodType<SearchResponse> = z
  .object({
    query: z.string(),
    results: z.array(SearchResult),
    total_matched: z.number().int(),
  })
  .passthrough();
const EconomicCalendarEvent = z
  .object({
    date: z.string(),
    category: z.enum(["FOMC", "EARNINGS", "EXPIRY", "MACRO"]),
    title: z.string(),
    impact: z.enum(["LOW", "MEDIUM", "HIGH"]),
  })
  .passthrough();
const InstrumentInfo: z.ZodType<InstrumentInfo> = z
  .object({
    symbol: z.string(),
    displayName: z.string(),
    exchange: z.string(),
    yfinanceTicker: z.string(),
  })
  .passthrough();
const UniverseResponse: z.ZodType<UniverseResponse> = z
  .object({
    instruments: z.array(InstrumentInfo),
    min_price: z.union([z.number(), z.null()]).optional(),
    max_price: z.union([z.number(), z.null()]).optional(),
    rsi_min: z.union([z.number(), z.null()]).optional(),
    rsi_max: z.union([z.number(), z.null()]).optional(),
    above_sma_200: z.union([z.boolean(), z.null()]).optional(),
    volume_surge: z.union([z.boolean(), z.null()]).optional(),
    ml_confidence_min: z.union([z.number(), z.null()]).optional(),
    sort_by: z.string().optional().default("market_cap"),
    sort_order: z
      .string()
      .regex(/^(asc|desc)$/)
      .optional()
      .default("desc"),
    limit: z.number().int().gte(1).lte(500).optional().default(50),
    offset: z.number().int().gte(0).optional().default(0),
  })
  .passthrough();
const app__schemas__regime__RegimeCurrentResponse = z
  .object({
    state: z.string(),
    state_index: z.number().int().gte(0).lte(3),
    probs: z.array(z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)),
    transition_matrix: z.array(
      z.array(z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/))
    ),
    cond_vol_1d: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    cond_vol_5d: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    cond_vol_21d: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    days_in_state: z.number().int(),
    last_transition_date: z.string().datetime({ offset: true }),
    timestamp: z.string().datetime({ offset: true }),
  })
  .passthrough();
const app__schemas__regime__RegimeHistoryPoint: z.ZodType<app__schemas__regime__RegimeHistoryPoint> =
  z
    .object({
      time: z.string().datetime({ offset: true }),
      state: z.string(),
      state_index: z.number().int(),
      probs: z.array(z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)),
      cond_vol: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
      cond_vol_5d: z.union([z.string(), z.null()]).optional(),
      cond_vol_21d: z.union([z.string(), z.null()]).optional(),
    })
    .passthrough();
const RegimeHistoryResponse: z.ZodType<RegimeHistoryResponse> = z
  .object({
    period_days: z.number().int(),
    start_date: z.string().datetime({ offset: true }),
    end_date: z.string().datetime({ offset: true }),
    data: z.array(app__schemas__regime__RegimeHistoryPoint),
    transitions: z.number().int(),
  })
  .passthrough();
const RegimeStatisticsItem = z
  .object({
    state: z.enum(["BULL", "BEAR", "SIDEWAYS", "CRISIS"]),
    avg_duration: z.number(),
    avg_return: z.number(),
    avg_vol: z.number(),
    freq: z.number(),
  })
  .passthrough();
const app__schemas__intelligence__SHAPContribution: z.ZodType<app__schemas__intelligence__SHAPContribution> =
  z
    .object({
      name: z.string(),
      shap_val: z.number(),
      feature_val: z.number(),
      pct_rank: z.number(),
    })
    .passthrough();
const ExplainShapResponse: z.ZodType<ExplainShapResponse> = z
  .object({
    model: z.string(),
    feature_contributions: z.array(
      app__schemas__intelligence__SHAPContribution
    ),
    base_value: z.number(),
    output_value: z.number(),
    waterfall_ready: z.boolean(),
  })
  .passthrough();
const AttentionTopTimestep: z.ZodType<AttentionTopTimestep> = z
  .object({ date: z.string(), weight: z.number() })
  .passthrough();
const ExplainAttentionResponse: z.ZodType<ExplainAttentionResponse> = z
  .object({
    model: z.enum(["tft", "lstm_attn"]),
    weights: z.array(z.array(z.number())),
    mean_weights: z.array(z.number()),
    top_timesteps: z.array(AttentionTopTimestep),
  })
  .passthrough();
const app__schemas__intelligence__CounterfactualRequest = z
  .object({
    target_direction: z.enum(["BUY", "SELL"]),
    num_cfs: z.number().int().gte(1).lte(10).optional().default(5),
  })
  .passthrough();
const CounterfactualFeatureChange: z.ZodType<CounterfactualFeatureChange> = z
  .object({
    name: z.string(),
    original: z.number(),
    counterfactual: z.number(),
  })
  .passthrough();
const app__schemas__intelligence__CounterfactualResponse: z.ZodType<app__schemas__intelligence__CounterfactualResponse> =
  z
    .object({
      cf_id: z.string(),
      changed_features: z.array(CounterfactualFeatureChange),
      resulting_signal: z.enum([
        "STRONG_BUY",
        "BUY",
        "NEUTRAL",
        "SELL",
        "STRONG_SELL",
      ]),
      proximity_score: z.number(),
    })
    .passthrough();
const WalkForwardConfig: z.ZodType<WalkForwardConfig> = z
  .object({
    enabled: z.boolean().default(true),
    n_splits: z.number().int().gte(2).lte(20).default(8),
    purge_days: z.number().int().gte(0).default(5),
    embargo_days: z.number().int().gte(0).default(5),
  })
  .partial()
  .passthrough();
const MonteCarloConfig: z.ZodType<MonteCarloConfig> = z
  .object({
    enabled: z.boolean().default(true),
    n_simulations: z.number().int().gte(100).lte(100000).default(10000),
  })
  .partial()
  .passthrough();
const BacktestRequest: z.ZodType<BacktestRequest> = z
  .object({
    strategy_name: z.string(),
    strategy_params: z.object({}).partial().passthrough().optional(),
    universe: z.array(z.string()).min(1).max(500),
    date_from: z.string(),
    date_to: z.string(),
    initial_capital: z.union([z.number(), z.string()]),
    walk_forward: z.union([WalkForwardConfig, z.null()]).optional(),
    monte_carlo: z.union([MonteCarloConfig, z.null()]).optional(),
  })
  .passthrough();
const BacktestRunResponse = z
  .object({
    job_id: z.string(),
    status: z.string().optional().default("PENDING"),
    estimated_seconds: z.number().int(),
    universe_size: z.number().int(),
    period_days: z.number().int(),
    strategy_name: z.string().optional().default("custom"),
  })
  .passthrough();
const BacktestStatusResponse = z
  .object({
    job_id: z.string(),
    status: z.string(),
    progress_pct: z.number().int().gte(0).lte(100),
    current_date: z.union([z.string(), z.null()]).optional(),
    equity_value: z.union([z.string(), z.null()]).optional(),
    estimated_remaining_seconds: z.union([z.number(), z.null()]).optional(),
    error_message: z.union([z.string(), z.null()]).optional(),
    result_preview: z
      .union([z.object({}).partial().passthrough(), z.null()])
      .optional(),
  })
  .passthrough();
const BacktestMetrics: z.ZodType<BacktestMetrics> = z
  .object({
    total_return: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    cagr: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    sharpe: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    sharpe_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    sortino_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    calmar_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    omega_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    max_drawdown: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    max_drawdown_duration_days: z.number().int(),
    win_rate: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    profit_factor: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    avg_win: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    avg_loss: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    payoff_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    num_trades: z.number().int(),
    gross_profit: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    gross_loss: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    tail_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    serenity_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    deflated_sharpe: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const EquityCurvePoint: z.ZodType<EquityCurvePoint> = z
  .object({
    date: z.string(),
    portfolio_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    benchmark_value: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const DrawdownPoint: z.ZodType<DrawdownPoint> = z
  .object({
    date: z.string(),
    drawdown_pct: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const TradeLogEntry: z.ZodType<TradeLogEntry> = z
  .object({
    date: z.string(),
    symbol: z.string(),
    direction: z.string(),
    quantity: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    price: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    pnl: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    cum_pnl: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    commission: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const WalkForwardMetrics: z.ZodType<WalkForwardMetrics> = z
  .object({
    fold_sharpes: z.array(z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)),
    mean_sharpe: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    std_sharpe: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    t_statistic: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    p_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const MonteCarloResults: z.ZodType<MonteCarloResults> = z
  .object({
    percentiles: z.record(z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)),
    prob_of_ruin_10pct: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    prob_of_ruin_25pct: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    fan_paths_sample: z.array(
      z.array(z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/))
    ),
  })
  .passthrough();
const StatisticalTests: z.ZodType<StatisticalTests> = z
  .object({
    dm_test_statistic: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    dm_test_p_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    dm_test_vs_benchmark: z.string().optional().default("ARIMA"),
    sharpe_se: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    min_backtest_length_days: z.number().int(),
    multiple_testing_correction: z.string().optional().default("Bonferroni"),
  })
  .passthrough();
const BacktestResultsResponse: z.ZodType<BacktestResultsResponse> = z
  .object({
    job_id: z.string(),
    strategy_name: z.string(),
    universe: z.array(z.string()),
    date_from: z.string(),
    date_to: z.string(),
    initial_capital: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    metrics: BacktestMetrics,
    equity_curve: z.array(EquityCurvePoint),
    drawdown_series: z.array(DrawdownPoint),
    trade_log: z.array(TradeLogEntry),
    walk_forward: z.union([WalkForwardMetrics, z.null()]).optional(),
    monte_carlo: z.union([MonteCarloResults, z.null()]).optional(),
    statistical_tests: z.union([StatisticalTests, z.null()]).optional(),
    status: z.string().optional().default("DONE"),
    completed_at: z.string().datetime({ offset: true }),
    excluded_tickers: z
      .union([z.array(z.object({}).partial().passthrough()), z.null()])
      .optional(),
  })
  .passthrough();
const HoldingData: z.ZodType<HoldingData> = z
  .object({
    symbol: z.string(),
    quantity: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    avg_price: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    current_price: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    unrealized_pnl: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    unrealized_pnl_pct: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    in_position_days: z.number().int(),
  })
  .passthrough();
const HoldingsResponse: z.ZodType<HoldingsResponse> = z
  .object({
    holdings: z.array(HoldingData),
    total_invested: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    total_current_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    total_unrealized_pnl: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    total_unrealized_pnl_pct: z
      .string()
      .regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    cash_balance: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    portfolio_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    timestamp: z.string().datetime({ offset: true }),
  })
  .passthrough();
const PerformancePoint: z.ZodType<PerformancePoint> = z
  .object({
    date: z.string().datetime({ offset: true }),
    portfolio_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    benchmark_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    daily_return: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    benchmark_return: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const PerformanceResponse: z.ZodType<PerformanceResponse> = z
  .object({
    series: z.array(PerformancePoint),
    start_date: z.string().datetime({ offset: true }),
    end_date: z.string().datetime({ offset: true }),
    total_return: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    benchmark_return: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    excess_return: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const TransactionRequest = z
  .object({
    symbol: z.string(),
    type: z.string(),
    quantity: z.union([z.number(), z.string()]),
    price: z.union([z.number(), z.string()]),
    brokerage: z
      .union([z.number(), z.string(), z.null()])
      .optional()
      .default(0),
    stt: z.union([z.number(), z.string(), z.null()]).optional().default(0),
  })
  .passthrough();
const TransactionResponse = z
  .object({
    transaction_id: z.string(),
    symbol: z.string(),
    type: z.string(),
    quantity: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    price: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    net_amount: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    timestamp: z.string().datetime({ offset: true }),
    portfolio_updated: z.boolean(),
  })
  .passthrough();
const RiskMetricsResponse = z
  .object({
    sharpe_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    sortino_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    beta: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    alpha: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    max_drawdown: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    var_95: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    cvar_95: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    treynor_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    information_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    calmar_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    portfolio_volatility: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    benchmark_volatility: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const OptimizationConstraints: z.ZodType<OptimizationConstraints> = z
  .object({
    max_weight: z.union([z.number(), z.string()]).default("0.20"),
    min_weight: z.union([z.number(), z.string()]).default("0.0"),
    sector_limits: z.union([
      z.record(z.union([z.number(), z.string()])),
      z.null(),
    ]),
    max_turnover: z.union([z.number(), z.string(), z.null()]),
    leverage_limit: z.union([z.number(), z.string()]).default("1.0"),
  })
  .partial()
  .passthrough();
const OptimizationRequest: z.ZodType<OptimizationRequest> = z
  .object({
    universe: z.array(z.string()).min(2).max(500),
    method: z.string(),
    constraints: z.union([OptimizationConstraints, z.null()]).optional(),
    use_ml_views: z.boolean().optional().default(true),
  })
  .passthrough();
const OptimizedWeight: z.ZodType<OptimizedWeight> = z
  .object({
    symbol: z.string(),
    weight: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const EfficientFrontierPoint: z.ZodType<EfficientFrontierPoint> = z
  .object({
    expected_return: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    expected_volatility: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    sharpe_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    weights: z.record(z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)),
  })
  .passthrough();
const OptimizationResponse: z.ZodType<OptimizationResponse> = z
  .object({
    method: z.string(),
    weights: z.array(OptimizedWeight),
    expected_return: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    expected_volatility: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    sharpe_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    efficient_frontier: z
      .union([z.array(EfficientFrontierPoint), z.null()])
      .optional(),
    hrp_dendrogram: z
      .union([z.object({}).partial().passthrough(), z.null()])
      .optional(),
    bl_posterior_returns: z
      .union([
        z.record(z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)),
        z.null(),
      ])
      .optional(),
    excluded_tickers: z
      .union([z.array(z.object({}).partial().passthrough()), z.null()])
      .optional(),
    timestamp: z.string().datetime({ offset: true }),
  })
  .passthrough();
const OrderRequest = z
  .object({
    symbol: z.string(),
    side: z.enum(["BUY", "SELL"]),
    quantity: z.number().gt(0),
    order_type: z.enum(["MARKET", "LIMIT"]),
    limit_price: z.union([z.number(), z.null()]).optional(),
    signal_relation: z
      .union([
        z.enum(["AGREEMENT", "AGAINST", "INDEPENDENT", "AUTO"]),
        z.null(),
      ])
      .optional()
      .default("AUTO"),
  })
  .passthrough();
const ScreenerFilterConfig: z.ZodType<ScreenerFilterConfig> = z
  .object({
    asset_class: z.union([z.string(), z.null()]),
    exchange: z.union([z.array(z.string()), z.string(), z.null()]),
    market_cap_min: z.union([z.number(), z.string(), z.null()]),
    market_cap_max: z.union([z.number(), z.string(), z.null()]),
    pe_ratio_max: z.union([z.number(), z.string(), z.null()]),
    rsi_min: z.union([z.number(), z.string(), z.null()]),
    rsi_max: z.union([z.number(), z.string(), z.null()]),
    momentum_21d_min: z.union([z.number(), z.string(), z.null()]),
    volume_ratio_min: z.union([z.number(), z.string(), z.null()]),
    signal_direction: z.union([z.array(z.string()), z.string(), z.null()]),
    regime_compatible: z.boolean().default(false),
    min_market_cap: z.union([z.number(), z.string(), z.null()]),
    max_market_cap: z.union([z.number(), z.string(), z.null()]),
    above_sma_200: z.union([z.boolean(), z.null()]),
    volume_surge: z.union([z.boolean(), z.null()]),
    ml_confidence_min: z.union([z.number(), z.string(), z.null()]),
  })
  .partial()
  .passthrough();
const ScreenerRunRequest: z.ZodType<ScreenerRunRequest> = z
  .object({
    exchange: z.array(z.string()),
    filters: ScreenerFilterConfig,
    sort_by: z.string().optional().default("sharpe_21d"),
    limit: z.number().int().gte(1).lte(500).optional().default(50),
  })
  .passthrough();
const ScreenerResult: z.ZodType<ScreenerResult> = z
  .object({
    ticker: z.string(),
    name: z.string(),
    exchange: z.string(),
    asset_type: z.string(),
    price: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    change_pct: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    pe_ratio: z.union([z.string(), z.null()]).optional(),
    rsi: z.union([z.string(), z.null()]).optional(),
    signal_direction: z.string(),
    signal_confidence: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    regime_state: z.string(),
    momentum_21d: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    volume_ratio: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const ScreenerRunResponse: z.ZodType<ScreenerRunResponse> = z
  .object({
    results: z.array(ScreenerResult),
    total_matched: z.number().int(),
    filters_applied: z.object({}).partial().passthrough(),
    generated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const ScreenerPreset: z.ZodType<ScreenerPreset> = z
  .object({
    name: z.string(),
    description: z.string(),
    filters_json: z.object({}).partial().passthrough(),
    created_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const ScreenerPresetsResponse: z.ZodType<ScreenerPresetsResponse> = z
  .object({ presets: z.array(ScreenerPreset) })
  .passthrough();
const ModelAccuracyItem = z
  .object({
    model: z.enum([
      "tft",
      "hmm_garch",
      "gnn",
      "lstm_attn",
      "xgboost",
      "ensemble",
    ]),
    precision: z.number(),
    recall: z.number(),
    directional_accuracy: z.number(),
    p50_rmse: z.number(),
    winkler_coverage_score: z.number(),
  })
  .passthrough();
const DriftItem = z
  .object({
    model: z.enum([
      "tft",
      "hmm_garch",
      "gnn",
      "lstm_attn",
      "xgboost",
      "ensemble",
    ]),
    adwin_p_value: z.number(),
    drift_detected: z.boolean(),
    residual_distribution: z.array(z.number()),
    ks_stat: z.number(),
  })
  .passthrough();
const app__schemas__intelligence__EnsembleWeightPoint = z
  .object({
    date: z.string(),
    tft: z.number(),
    hmm_garch: z.number(),
    gnn: z.number(),
    lstm_attn: z.number(),
    xgboost: z.number(),
  })
  .passthrough();
const CorrelationNode: z.ZodType<CorrelationNode> = z
  .object({
    ticker: z.string(),
    sector: z.string(),
    x: z.number(),
    y: z.number(),
    size: z.number(),
  })
  .passthrough();
const CorrelationEdge: z.ZodType<CorrelationEdge> = z
  .object({ source: z.string(), target: z.string(), correlation: z.number() })
  .passthrough();
const CorrelationGraphResponse: z.ZodType<CorrelationGraphResponse> = z
  .object({
    window_days: z.number().int(),
    central_asset: z.string(),
    nodes: z.array(CorrelationNode),
    edges: z.array(CorrelationEdge),
    top_correlates: z.array(z.record(z.union([z.number(), z.string()]))),
  })
  .passthrough();
const FactorExposureItem: z.ZodType<FactorExposureItem> = z
  .object({ factor: z.string(), beta: z.number() })
  .passthrough();
const FactorExposureResponse: z.ZodType<FactorExposureResponse> = z
  .object({
    symbol: z.string(),
    window_days: z.number().int(),
    exposures: z.array(FactorExposureItem),
    metrics: z.record(z.number()),
  })
  .passthrough();
const SignalHistoryPoint = z
  .object({
    timestamp: z.string().datetime({ offset: true }),
    signal: z.number(),
    actual_return: z.number(),
    model: z.string(),
  })
  .passthrough();
const app__schemas__intelligence__RegimeCurrentResponse = z
  .object({
    state: z.enum(["BULL", "BEAR", "SIDEWAYS", "CRISIS"]),
    probs: z.record(z.number()),
    transition_matrix: z.array(z.array(z.number())),
    cond_vol_1d: z.number(),
    cond_vol_5d: z.number(),
    cond_vol_21d: z.number(),
    days_in_state: z.number().int(),
    last_transition_date: z.string(),
  })
  .passthrough();
const app__schemas__intelligence__RegimeHistoryPoint = z
  .object({
    time: z.string(),
    state: z.enum(["BULL", "BEAR", "SIDEWAYS", "CRISIS"]),
    probs: z.record(z.number()),
    cond_vol: z.number(),
  })
  .passthrough();
const ForecastRequest = z
  .object({
    symbol: z.string(),
    horizons: z.array(z.string()).optional().default(["1d", "1w", "1mo"]),
    models: z.union([z.array(z.string()), z.null()]).optional(),
  })
  .passthrough();
const JournalResponse = z
  .object({
    id: z.string().uuid(),
    user_id: z.string().uuid(),
    symbol: z.string(),
    notes: z.string(),
    tags: z.union([z.string(), z.null()]).optional(),
    rating: z.union([z.number(), z.null()]).optional(),
    entry_price: z.union([z.string(), z.null()]).optional(),
    exit_price: z.union([z.string(), z.null()]).optional(),
    quantity: z.union([z.string(), z.null()]).optional(),
    direction: z.union([z.string(), z.null()]).optional(),
    created_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const JournalCreate = z
  .object({
    symbol: z.string().min(1).max(32),
    notes: z.string().max(1024),
    tags: z.union([z.string(), z.null()]).optional(),
    rating: z.union([z.number(), z.null()]).optional(),
    entry_price: z.union([z.number(), z.string(), z.null()]).optional(),
    exit_price: z.union([z.number(), z.string(), z.null()]).optional(),
    quantity: z.union([z.number(), z.string(), z.null()]).optional(),
    direction: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const AttentionTimestep: z.ZodType<AttentionTimestep> = z
  .object({
    date: z.string().datetime({ offset: true }),
    weight: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const AttentionResponse: z.ZodType<AttentionResponse> = z
  .object({
    symbol: z.string(),
    model: z.string(),
    weights: z.array(
      z.array(z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/))
    ),
    mean_weights: z.array(z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/)),
    top_timesteps: z.array(AttentionTimestep).max(10),
    num_heads: z.number().int(),
    num_timesteps: z.number().int(),
    timestamp: z.string().datetime({ offset: true }),
  })
  .passthrough();
const FeatureChange: z.ZodType<FeatureChange> = z
  .object({
    name: z.string(),
    original_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    counterfactual_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    change_pct: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const CounterfactualInstance: z.ZodType<CounterfactualInstance> = z
  .object({
    cf_id: z.string(),
    changed_features: z.array(FeatureChange),
    resulting_signal: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    resulting_confidence: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    proximity_score: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const DriftDistribution: z.ZodType<DriftDistribution> = z
  .object({
    mean: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    std: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    p25: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    p50: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    p75: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    min: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    max: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const ModelDriftMetrics: z.ZodType<ModelDriftMetrics> = z
  .object({
    model_name: z.string(),
    adwin_p_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    drift_detected: z.boolean(),
    ks_statistic: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    ks_p_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    residual_distribution_now: DriftDistribution,
    residual_distribution_baseline: DriftDistribution,
    days_since_retrain: z.number().int(),
    last_retraining_date: z.string().datetime({ offset: true }),
    as_of_date: z.string().datetime({ offset: true }),
  })
  .passthrough();
const DriftResponse: z.ZodType<DriftResponse> = z
  .object({
    models: z.array(ModelDriftMetrics),
    overall_drift_detected: z.boolean(),
    generated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const EconomicEvent: z.ZodType<EconomicEvent> = z
  .object({
    date: z.string().datetime({ offset: true }),
    event_name: z.string(),
    country: z.string(),
    importance: z.string(),
    forecast: z.union([z.string(), z.null()]).optional(),
    previous: z.union([z.string(), z.null()]).optional(),
  })
  .passthrough();
const EconomicCalendarResponse: z.ZodType<EconomicCalendarResponse> = z
  .object({
    events: z.array(EconomicEvent),
    period_start: z.string().datetime({ offset: true }),
    period_end: z.string().datetime({ offset: true }),
  })
  .passthrough();
const ModelAccuracyMetrics: z.ZodType<ModelAccuracyMetrics> = z
  .object({
    model_name: z.string(),
    period_days: z.number().int().optional().default(21),
    precision: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    recall: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    f1_score: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    directional_accuracy: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    p50_rmse: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    winkler_coverage: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    as_of_date: z.string().datetime({ offset: true }),
  })
  .passthrough();
const ModelAccuracyResponse: z.ZodType<ModelAccuracyResponse> = z
  .object({
    models: z.array(ModelAccuracyMetrics),
    benchmark_ensemble_accuracy: z
      .string()
      .regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    generated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
const RegimeStatistics: z.ZodType<RegimeStatistics> = z
  .object({
    state: z.string(),
    state_index: z.number().int(),
    avg_duration_days: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    frequency_pct: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    avg_daily_return: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    avg_volatility: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    min_volatility: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    max_volatility: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    best_daily_return: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    worst_daily_return: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const RegimeStatisticsResponse: z.ZodType<RegimeStatisticsResponse> = z
  .object({
    period_days: z.number().int(),
    statistics: z.array(RegimeStatistics),
    most_common_state: z.string(),
    mean_duration_all_states: z
      .string()
      .regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
  })
  .passthrough();
const app__schemas__explain__SHAPContribution: z.ZodType<app__schemas__explain__SHAPContribution> =
  z
    .object({
      name: z.string(),
      shap_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
      feature_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
      percentile_rank: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    })
    .passthrough();
const SHAPResponse: z.ZodType<SHAPResponse> = z
  .object({
    symbol: z.string(),
    model: z.string(),
    feature_contributions: z.array(app__schemas__explain__SHAPContribution),
    base_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    output_value: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    waterfall_ready: z.boolean().optional().default(true),
    timestamp: z.string().datetime({ offset: true }),
  })
  .passthrough();
const app__schemas__monitor__EnsembleWeightPoint: z.ZodType<app__schemas__monitor__EnsembleWeightPoint> =
  z
    .object({
      date: z.string().datetime({ offset: true }),
      tft: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
      hmm_garch: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
      gnn: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
      lstm_attn: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
      xgboost: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
    })
    .passthrough();
const WeightsHistoryResponse: z.ZodType<WeightsHistoryResponse> = z
  .object({
    period_days: z.number().int().optional().default(252),
    data: z.array(app__schemas__monitor__EnsembleWeightPoint),
    start_date: z.string().datetime({ offset: true }),
    end_date: z.string().datetime({ offset: true }),
  })
  .passthrough();
const app__schemas__explain__CounterfactualRequest = z
  .object({
    target_direction: z.string(),
    num_cfs: z.number().int().gte(1).lte(20).optional().default(5),
  })
  .passthrough();
const app__schemas__explain__CounterfactualResponse: z.ZodType<app__schemas__explain__CounterfactualResponse> =
  z
    .object({
      symbol: z.string(),
      target_direction: z.string(),
      counterfactuals: z.array(CounterfactualInstance),
      original_signal: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
      original_confidence: z.string().regex(/^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$/),
      timestamp: z.string().datetime({ offset: true }),
    })
    .passthrough();

export const schemas = {
  AuthRegister,
  ValidationError,
  HTTPValidationError,
  AuthLogin,
  TokenResponse,
  AuthRefresh,
  UserProfileResponse,
  UpdateProfileRequest,
  OrganizationResponse,
  MemberResponse,
  InviteRequest,
  ApiKeyCreate,
  BlogPostCreate,
  BlogPostUpdate,
  NotificationCreate,
  SubscriptionResponse,
  WatchlistResponse,
  WatchlistAddRequest,
  AlertCreate,
  RegimeData,
  SignalData,
  QuoteResponse,
  period,
  OHLCVBar,
  HistoryResponse,
  IndexData,
  IndicesResponse,
  MoverData,
  MoversResponse,
  SectorNode,
  HeatmapResponse,
  SearchResult,
  SearchResponse,
  EconomicCalendarEvent,
  InstrumentInfo,
  UniverseResponse,
  app__schemas__regime__RegimeCurrentResponse,
  app__schemas__regime__RegimeHistoryPoint,
  RegimeHistoryResponse,
  RegimeStatisticsItem,
  app__schemas__intelligence__SHAPContribution,
  ExplainShapResponse,
  AttentionTopTimestep,
  ExplainAttentionResponse,
  app__schemas__intelligence__CounterfactualRequest,
  CounterfactualFeatureChange,
  app__schemas__intelligence__CounterfactualResponse,
  WalkForwardConfig,
  MonteCarloConfig,
  BacktestRequest,
  BacktestRunResponse,
  BacktestStatusResponse,
  BacktestMetrics,
  EquityCurvePoint,
  DrawdownPoint,
  TradeLogEntry,
  WalkForwardMetrics,
  MonteCarloResults,
  StatisticalTests,
  BacktestResultsResponse,
  HoldingData,
  HoldingsResponse,
  PerformancePoint,
  PerformanceResponse,
  TransactionRequest,
  TransactionResponse,
  RiskMetricsResponse,
  OptimizationConstraints,
  OptimizationRequest,
  OptimizedWeight,
  EfficientFrontierPoint,
  OptimizationResponse,
  OrderRequest,
  ScreenerFilterConfig,
  ScreenerRunRequest,
  ScreenerResult,
  ScreenerRunResponse,
  ScreenerPreset,
  ScreenerPresetsResponse,
  ModelAccuracyItem,
  DriftItem,
  app__schemas__intelligence__EnsembleWeightPoint,
  CorrelationNode,
  CorrelationEdge,
  CorrelationGraphResponse,
  FactorExposureItem,
  FactorExposureResponse,
  SignalHistoryPoint,
  app__schemas__intelligence__RegimeCurrentResponse,
  app__schemas__intelligence__RegimeHistoryPoint,
  ForecastRequest,
  JournalResponse,
  JournalCreate,
  AttentionTimestep,
  AttentionResponse,
  FeatureChange,
  CounterfactualInstance,
  DriftDistribution,
  ModelDriftMetrics,
  DriftResponse,
  EconomicEvent,
  EconomicCalendarResponse,
  ModelAccuracyMetrics,
  ModelAccuracyResponse,
  RegimeStatistics,
  RegimeStatisticsResponse,
  app__schemas__explain__SHAPContribution,
  SHAPResponse,
  app__schemas__monitor__EnsembleWeightPoint,
  WeightsHistoryResponse,
  app__schemas__explain__CounterfactualRequest,
  app__schemas__explain__CounterfactualResponse,
};

const endpoints = makeApi([
  {
    method: "get",
    path: "/api/v1/admin/content",
    alias: "content_control_api_v1_admin_content_get",
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "post",
    path: "/api/v1/admin/ingest",
    alias: "trigger_ingestion_api_v1_admin_ingest_post",
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "get",
    path: "/api/v1/admin/users",
    alias: "list_users_api_v1_admin_users_get",
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "patch",
    path: "/api/v1/admin/users/:user_id/role",
    alias: "update_user_role_api_v1_admin_users__user_id__role_patch",
    requestFormat: "json",
    parameters: [
      {
        name: "user_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/alerts",
    alias: "list_alerts_api_v1_alerts_get",
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "post",
    path: "/api/v1/alerts",
    alias: "create_alert_api_v1_alerts_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: AlertCreate,
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/auth/login",
    alias: "login_api_v1_auth_login_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: AuthLogin,
      },
    ],
    response: TokenResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/auth/logout",
    alias: "logout_api_v1_auth_logout_post",
    requestFormat: "json",
    response: z.void(),
  },
  {
    method: "get",
    path: "/api/v1/auth/me",
    alias: "me_api_v1_auth_me_get",
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "post",
    path: "/api/v1/auth/refresh",
    alias: "refresh_api_v1_auth_refresh_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z.object({ refresh_token: z.string() }).passthrough(),
      },
    ],
    response: TokenResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/auth/register",
    alias: "register_api_v1_auth_register_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: AuthRegister,
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/backtest/results/:job_id",
    alias: "get_backtest_results_api_v1_backtest_results__job_id__get",
    requestFormat: "json",
    parameters: [
      {
        name: "job_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: BacktestResultsResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/backtest/run",
    alias: "post_backtest_run_api_v1_backtest_run_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BacktestRequest,
      },
    ],
    response: BacktestRunResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/backtest/status/:job_id",
    alias: "get_backtest_status_api_v1_backtest_status__job_id__get",
    requestFormat: "json",
    parameters: [
      {
        name: "job_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: BacktestStatusResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/blog/posts",
    alias: "list_posts_api_v1_blog_posts_get",
    requestFormat: "json",
    parameters: [
      {
        name: "limit",
        type: "Query",
        schema: z.number().int().optional().default(20),
      },
    ],
    response: z.object({}).partial().passthrough(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/blog/posts",
    alias: "create_post_api_v1_blog_posts_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BlogPostCreate,
      },
    ],
    response: z.record(z.string()),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/blog/posts/:slug",
    alias: "get_post_api_v1_blog_posts__slug__get",
    requestFormat: "json",
    parameters: [
      {
        name: "slug",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.object({}).partial().passthrough(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "patch",
    path: "/api/v1/blog/posts/:slug",
    alias: "update_post_api_v1_blog_posts__slug__patch",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: BlogPostUpdate,
      },
      {
        name: "slug",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.record(z.string()),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/explain/attention/:symbol",
    alias: "get_attention_explainability_api_v1_explain_attention__symbol__get",
    description: `Return temporal attention weights from the requested sequence model.`,
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
      {
        name: "model",
        type: "Query",
        schema: z
          .string()
          .regex(/^(tft|lstm_attn)$/)
          .optional()
          .default("tft"),
      },
    ],
    response: ExplainAttentionResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/explain/counterfactual/:symbol",
    alias: "get_counterfactual_api_v1_explain_counterfactual__symbol__post",
    description: `Return counterfactual feature changes that can flip signal direction.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: app__schemas__intelligence__CounterfactualRequest,
      },
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.array(app__schemas__intelligence__CounterfactualResponse),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/explain/shap/:symbol",
    alias: "get_shap_explainability_api_v1_explain_shap__symbol__get",
    description: `Return SHAP feature attribution values for the latest inference.`,
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: ExplainShapResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/health",
    alias: "health_check_api_v1_health_get",
    description: `Application health check — returns service status.`,
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "get",
    path: "/api/v1/health/live-data",
    alias: "health_live_data_api_v1_health_live_data_get",
    description: `Pings external data sources to check reachability.`,
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "get",
    path: "/api/v1/journal",
    alias: "get_journals_api_v1_journal_get",
    description: `Retrieve all trade journal entries for the current user.`,
    requestFormat: "json",
    response: z.array(JournalResponse),
  },
  {
    method: "post",
    path: "/api/v1/journal",
    alias: "create_journal_api_v1_journal_post",
    description: `Create a new trade journal entry.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: JournalCreate,
      },
    ],
    response: JournalResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/journal/:journal_id",
    alias: "delete_journal_api_v1_journal__journal_id__delete",
    description: `Delete a trade journal entry by ID.`,
    requestFormat: "json",
    parameters: [
      {
        name: "journal_id",
        type: "Path",
        schema: z.string().uuid(),
      },
    ],
    response: z.void(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/market/economic-calendar",
    alias: "get_economic_calendar_api_v1_market_economic_calendar_get",
    description: `Return upcoming high-impact macro and market events.`,
    requestFormat: "json",
    response: z.array(EconomicCalendarEvent),
  },
  {
    method: "get",
    path: "/api/v1/market/global-context",
    alias: "get_global_context_api_v1_market_global_context_get",
    requestFormat: "json",
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "get",
    path: "/api/v1/market/heatmap",
    alias: "get_heatmap_api_v1_market_heatmap_get",
    requestFormat: "json",
    parameters: [
      {
        name: "exchange",
        type: "Query",
        schema: z.string().optional().default("NSE"),
      },
      {
        name: "metric",
        type: "Query",
        schema: z
          .string()
          .regex(/^(return_1d|return_5d|volume_surge)$/)
          .optional()
          .default("return_1d"),
      },
    ],
    response: HeatmapResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/market/history/:symbol",
    alias: "get_history_api_v1_market_history__symbol__get",
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
      {
        name: "interval",
        type: "Query",
        schema: z
          .string()
          .regex(/^(1m|3m|5m|10m|15m|30m|45m|1h|2h|4h|1d|1w|1mo)$/)
          .optional()
          .default("1d"),
      },
      {
        name: "period",
        type: "Query",
        schema: period,
      },
    ],
    response: HistoryResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/market/indices",
    alias: "get_indices_api_v1_market_indices_get",
    requestFormat: "json",
    response: IndicesResponse,
  },
  {
    method: "get",
    path: "/api/v1/market/movers",
    alias: "get_movers_api_v1_market_movers_get",
    requestFormat: "json",
    parameters: [
      {
        name: "exchange",
        type: "Query",
        schema: z.string().optional().default("NSE"),
      },
      {
        name: "type",
        type: "Query",
        schema: z
          .string()
          .regex(/^(gainers|losers|volume|momentum)$/)
          .optional()
          .default("gainers"),
      },
    ],
    response: MoversResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/market/providers/health",
    alias: "get_providers_health_api_v1_market_providers_health_get",
    requestFormat: "json",
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "get",
    path: "/api/v1/market/quote/:symbol",
    alias: "get_quote_api_v1_market_quote__symbol__get",
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: QuoteResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/market/search",
    alias: "search_symbols_api_v1_market_search_get",
    requestFormat: "json",
    parameters: [
      {
        name: "q",
        type: "Query",
        schema: z.string().min(2).max(50),
      },
    ],
    response: SearchResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/market/status",
    alias: "get_market_status_api_v1_market_status_get",
    requestFormat: "json",
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "get",
    path: "/api/v1/market/universe",
    alias: "get_market_universe_api_v1_market_universe_get",
    requestFormat: "json",
    response: UniverseResponse,
  },
  {
    method: "get",
    path: "/api/v1/monitor/drift",
    alias: "get_drift_api_v1_monitor_drift_get",
    description: `Return concept drift diagnostics for production model monitoring.`,
    requestFormat: "json",
    response: z.array(DriftItem),
  },
  {
    method: "get",
    path: "/api/v1/monitor/ensemble-weights-history",
    alias:
      "get_ensemble_weights_history_api_v1_monitor_ensemble_weights_history_get",
    description: `Return historical dynamic ensemble weights for model governance analysis.`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().gte(30).lte(504).optional().default(252),
      },
    ],
    response: z.array(app__schemas__intelligence__EnsembleWeightPoint),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/monitor/model-accuracy",
    alias: "get_model_accuracy_api_v1_monitor_model_accuracy_get",
    description: `Return rolling model quality metrics for each model family.`,
    requestFormat: "json",
    response: z.array(ModelAccuracyItem),
  },
  {
    method: "get",
    path: "/api/v1/news/:symbol",
    alias: "get_news_for_symbol_api_v1_news__symbol__get",
    description: `Get scraped news and sentiment for a specific symbol.`,
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/notifications",
    alias: "list_notifications_api_v1_notifications_get",
    requestFormat: "json",
    response: z.object({}).partial().passthrough(),
  },
  {
    method: "post",
    path: "/api/v1/notifications",
    alias: "create_notification_api_v1_notifications_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: NotificationCreate,
      },
    ],
    response: z.record(z.string()),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/notifications/:notification_id/read",
    alias: "mark_read_api_v1_notifications__notification_id__read_post",
    requestFormat: "json",
    parameters: [
      {
        name: "notification_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.record(z.string()),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/organizations",
    alias: "list_user_organizations_api_v1_organizations_get",
    requestFormat: "json",
    response: z.array(OrganizationResponse),
  },
  {
    method: "post",
    path: "/api/v1/organizations/:org_id/api-keys",
    alias: "create_api_key_api_v1_organizations__org_id__api_keys_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ApiKeyCreate,
      },
      {
        name: "org_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/organizations/:org_id/api-keys",
    alias: "list_api_keys_api_v1_organizations__org_id__api_keys_get",
    requestFormat: "json",
    parameters: [
      {
        name: "org_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/organizations/:org_id/invitations",
    alias: "invite_member_api_v1_organizations__org_id__invitations_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: InviteRequest,
      },
      {
        name: "org_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/organizations/:org_id/members",
    alias: "list_members_api_v1_organizations__org_id__members_get",
    requestFormat: "json",
    parameters: [
      {
        name: "org_id",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.array(MemberResponse),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/paper-trade/cancel/:order_id",
    alias: "cancel_order_api_v1_paper_trade_cancel__order_id__post",
    requestFormat: "json",
    parameters: [
      {
        name: "order_id",
        type: "Path",
        schema: z.string(),
      },
      {
        name: "symbol",
        type: "Query",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/paper-trade/history",
    alias: "get_history_api_v1_paper_trade_history_get",
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "post",
    path: "/api/v1/paper-trade/order",
    alias: "submit_order_api_v1_paper_trade_order_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: OrderRequest,
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/paper-trade/pnl",
    alias: "get_pnl_api_v1_paper_trade_pnl_get",
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "get",
    path: "/api/v1/paper-trade/positions",
    alias: "get_positions_api_v1_paper_trade_positions_get",
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "post",
    path: "/api/v1/paper-trade/reset",
    alias: "reset_wallet_api_v1_paper_trade_reset_post",
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "get",
    path: "/api/v1/payments/plans",
    alias: "get_plans_api_v1_payments_plans_get",
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "get",
    path: "/api/v1/payments/subscription",
    alias: "get_subscription_api_v1_payments_subscription_get",
    requestFormat: "json",
    response: z.union([SubscriptionResponse, z.null()]),
  },
  {
    method: "post",
    path: "/api/v1/payments/webhook",
    alias: "razorpay_webhook_api_v1_payments_webhook_post",
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "get",
    path: "/api/v1/portfolio",
    alias: "list_portfolios_api_v1_portfolio_get",
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "get",
    path: "/api/v1/portfolio/:portfolio_id",
    alias: "get_portfolio_api_v1_portfolio__portfolio_id__get",
    requestFormat: "json",
    parameters: [
      {
        name: "portfolio_id",
        type: "Path",
        schema: z.number().int(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/portfolio/holdings",
    alias: "get_holdings_api_v1_portfolio_holdings_get",
    description: `Return a holdings snapshot for the authenticated user.`,
    requestFormat: "json",
    response: HoldingsResponse,
  },
  {
    method: "post",
    path: "/api/v1/portfolio/optimize",
    alias: "post_optimize_api_v1_portfolio_optimize_post",
    description: `Return normalized optimization output for requested universe and method.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: OptimizationRequest,
      },
    ],
    response: OptimizationResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/portfolio/performance",
    alias: "get_performance_api_v1_portfolio_performance_get",
    description: `Return time-series portfolio performance based on live data and current holdings.`,
    requestFormat: "json",
    response: PerformanceResponse,
  },
  {
    method: "get",
    path: "/api/v1/portfolio/risk-metrics",
    alias: "get_risk_metrics_api_v1_portfolio_risk_metrics_get",
    description: `Return portfolio risk metrics based on actual historical performance.`,
    requestFormat: "json",
    response: RiskMetricsResponse,
  },
  {
    method: "post",
    path: "/api/v1/portfolio/transaction",
    alias: "post_transaction_api_v1_portfolio_transaction_post",
    description: `Record a transaction and update cash/holdings inside SQLAlchemy.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: TransactionRequest,
      },
    ],
    response: TransactionResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/predictions/:symbol",
    alias: "get_prediction_api_v1_predictions__symbol__get",
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/predictions/ensemble/:symbol",
    alias: "get_ensemble_data_api_v1_predictions_ensemble__symbol__get",
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/predictions/forecast",
    alias: "generate_forecast_api_v1_predictions_forecast_post",
    description: `Multi-horizon SARIMAX price forecast — real statistical forecasting on
real OHLCV history, not a stub. Each horizon reports the actual data
window it was fit on and an honest confidence label; horizons under 1h
are only ever backed by ~60 days of intraday data (a free-data-source
limit, not a modeling choice) and are labeled accordingly.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ForecastRequest,
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/predictions/history/:symbol",
    alias: "get_prediction_history_api_v1_predictions_history__symbol__get",
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/predictions/latest/:symbol",
    alias: "get_latest_forecast_api_v1_predictions_latest__symbol__get",
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/ready",
    alias: "readiness_check_api_v1_ready_get",
    description: `Readiness probe with dependency checks for DB and Redis.`,
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "get",
    path: "/api/v1/regime/:symbol/current",
    alias: "get_regime_current_api_v1_regime__symbol__current_get",
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: app__schemas__regime__RegimeCurrentResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/regime/:symbol/history",
    alias: "get_regime_history_api_v1_regime__symbol__history_get",
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
      {
        name: "days",
        type: "Query",
        schema: z.number().int().gte(1).lte(1000).optional().default(252),
      },
    ],
    response: RegimeHistoryResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/regime/current",
    alias: "get_regime_current_api_v1_regime_current_get",
    description: `Return current regime state, transition matrix, and conditional volatility.`,
    requestFormat: "json",
    response: app__schemas__intelligence__RegimeCurrentResponse,
  },
  {
    method: "get",
    path: "/api/v1/regime/history",
    alias: "get_regime_history_api_v1_regime_history_get",
    description: `Return daily regime labels and probabilities for the selected history window.`,
    requestFormat: "json",
    parameters: [
      {
        name: "days",
        type: "Query",
        schema: z.number().int().gte(30).lte(504).optional().default(252),
      },
    ],
    response: z.array(app__schemas__intelligence__RegimeHistoryPoint),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/regime/statistics",
    alias: "get_regime_statistics_api_v1_regime_statistics_get",
    description: `Return aggregate per-regime summary statistics.`,
    requestFormat: "json",
    response: z.array(RegimeStatisticsItem),
  },
  {
    method: "get",
    path: "/api/v1/research/correlation-graph",
    alias: "get_correlation_graph_api_v1_research_correlation_graph_get",
    description: `Return correlation graph nodes and edges for research workspace.`,
    requestFormat: "json",
    parameters: [
      {
        name: "window_days",
        type: "Query",
        schema: z.number().int().gte(30).lte(252).optional().default(60),
      },
    ],
    response: CorrelationGraphResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/research/factor-exposure",
    alias: "get_factor_exposure_api_v1_research_factor_exposure_get",
    description: `Return rolling factor exposures and diagnostics for selected symbol.`,
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Query",
        schema: z.string().min(2).optional().default("RELIANCE.NS"),
      },
      {
        name: "window_days",
        type: "Query",
        schema: z.number().int().gte(63).lte(504).optional().default(126),
      },
    ],
    response: FactorExposureResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/screener/presets",
    alias: "get_screener_presets_api_v1_screener_presets_get",
    requestFormat: "json",
    response: ScreenerPresetsResponse,
  },
  {
    method: "post",
    path: "/api/v1/screener/run",
    alias: "post_screener_run_api_v1_screener_run_post",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: ScreenerRunRequest,
      },
    ],
    response: ScreenerRunResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/signals/:symbol",
    alias: "get_signal_api_v1_signals__symbol__get",
    description: `Return the latest ensemble and model-level signal for a symbol.`,
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/signals/bulk",
    alias: "get_bulk_signals_api_v1_signals_bulk_get",
    description: `Return parallel signal snapshots for up to 50 symbols.`,
    requestFormat: "json",
    parameters: [
      {
        name: "symbols",
        type: "Query",
        schema: z.string(),
      },
    ],
    response: z.unknown(),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/signals/history/:symbol",
    alias: "get_signal_history_api_v1_signals_history__symbol__get",
    description: `Return historical signal series and realized returns for model evaluation.`,
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
      {
        name: "model",
        type: "Query",
        schema: z
          .string()
          .regex(/^(ensemble|tft|hmm_garch|gnn|lstm_attn|xgboost)$/)
          .optional()
          .default("ensemble"),
      },
      {
        name: "days",
        type: "Query",
        schema: z.number().int().gte(30).lte(252).optional().default(90),
      },
    ],
    response: z.array(SignalHistoryPoint),
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/users/profile",
    alias: "get_profile_api_v1_users_profile_get",
    requestFormat: "json",
    response: UserProfileResponse,
  },
  {
    method: "patch",
    path: "/api/v1/users/profile",
    alias: "update_profile_api_v1_users_profile_patch",
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: z
          .object({ full_name: z.string().min(1).max(120) })
          .passthrough(),
      },
    ],
    response: UserProfileResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/version",
    alias: "get_version_api_v1_version_get",
    requestFormat: "json",
    response: z.record(z.string()),
  },
  {
    method: "get",
    path: "/api/v1/watchlist",
    alias: "get_watchlist_api_v1_watchlist_get",
    description: `Retrieve the current user&#x27;s watchlist for a specific tab.`,
    requestFormat: "json",
    parameters: [
      {
        name: "list_id",
        type: "Query",
        schema: z.number().int().optional().default(0),
      },
    ],
    response: WatchlistResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "post",
    path: "/api/v1/watchlist",
    alias: "add_to_watchlist_api_v1_watchlist_post",
    description: `Add a symbol to the current user&#x27;s watchlist for a specific tab.`,
    requestFormat: "json",
    parameters: [
      {
        name: "body",
        type: "Body",
        schema: WatchlistAddRequest,
      },
    ],
    response: WatchlistResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "delete",
    path: "/api/v1/watchlist/:symbol",
    alias: "remove_from_watchlist_api_v1_watchlist__symbol__delete",
    description: `Remove a symbol from the current user&#x27;s watchlist tab.`,
    requestFormat: "json",
    parameters: [
      {
        name: "symbol",
        type: "Path",
        schema: z.string(),
      },
      {
        name: "list_id",
        type: "Query",
        schema: z.number().int().optional().default(0),
      },
    ],
    response: WatchlistResponse,
    errors: [
      {
        status: 422,
        description: `Validation Error`,
        schema: HTTPValidationError,
      },
    ],
  },
  {
    method: "get",
    path: "/api/v1/ws_url",
    alias: "get_ws_url_api_v1_ws_url_get",
    description: `Return the WebSocket URL for clients.

Allows front‑end to query the backend for the correct WS endpoint,
which can be overridden via the &#x60;WEBSOCKET_URL&#x60; environment variable.`,
    requestFormat: "json",
    response: z.record(z.string()),
  },
  {
    method: "get",
    path: "/health",
    alias: "health_check_health_get",
    requestFormat: "json",
    response: z.unknown(),
  },
  {
    method: "get",
    path: "/liveness",
    alias: "liveness_liveness_get",
    requestFormat: "json",
    response: z.record(z.string()),
  },
  {
    method: "get",
    path: "/readiness",
    alias: "readiness_readiness_get",
    requestFormat: "json",
    response: z.record(z.string()),
  },
]);

export const api = new Zodios(endpoints);

export function createApiClient(baseUrl: string, options?: ZodiosOptions) {
  return new Zodios(baseUrl, endpoints, options);
}
