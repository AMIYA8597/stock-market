export type SignalDirection =
  | "STRONG_BUY"
  | "BUY"
  | "NEUTRAL"
  | "SELL"
  | "STRONG_SELL";

export interface EnsembleSignal {
  signal: SignalDirection;
  confidence: number;
  direction: SignalDirection;
  kelly_fraction: number;
}

export interface RegimeDetails {
  state: "BULL" | "BEAR" | "SIDEWAYS" | "CRISIS";
  probs: Record<string, number>;
  transition_probs: Record<string, number>;
}

export interface TFTSignal {
  p10: number;
  p50: number;
  p90: number;
  raw_signal: number;
  horizon_days: number;
}

export interface HMMGarchSignal {
  regime_signal: string;
  vol_forecast_1d: number;
  vol_forecast_21d: number;
}

export interface GNNSignal {
  spillover_risk: number;
  embedding_norm: number;
  top_correlated_assets: string[];
}

export interface LSTMAttnSignal {
  raw_signal: number;
  attention_peaks: Array<Record<string, number>>;
}

export interface XGBoostSignal {
  raw_signal: number;
  top_features: Array<Record<string, string | number>>;
  xgb_confidence?: number;
  xgb_direction?: string;
  train_samples?: number;
}

export interface TechnicalModelSignal {
  score?: number;
  rsi?: number;
  macd_histogram?: number;
  bb_position?: number;
  adx?: number;
  supertrend_direction?: number;
  above_vwap?: boolean;
  indicators_computed?: number;
  atr?: number;
  ema9?: number;
  ema21?: number;
  ema50?: number;
  ema200?: number;
}

export interface PatternModelSignal {
  pattern_score?: number;
  patterns_detected?: string[];
  bullish_count?: number;
  bearish_count?: number;
}

export interface MomentumModelSignal {
  momentum_score?: number;
  ret_1d?: number;
  ret_5d?: number;
  ret_21d?: number;
  jt_momentum?: number;
  vol_21d?: number;
  yang_zhang_vol?: number;
  dist_52w_high?: number;
  dist_52w_low?: number;
}

export interface RegimeModelSignal {
  regime?: string;
  bull_prob?: number;
  bear_prob?: number;
  regime_confidence?: number;
  hmm_used?: boolean;
}

export interface SignalResponse {
  symbol: string;
  timestamp: string;
  ensemble: EnsembleSignal;
  models: {
    tft: TFTSignal;
    hmm_garch: HMMGarchSignal;
    gnn: GNNSignal;
    lstm_attn: LSTMAttnSignal;
    xgboost: XGBoostSignal;
    technical?: TechnicalModelSignal;
    pattern?: PatternModelSignal;
    momentum?: MomentumModelSignal;
    regime?: RegimeModelSignal;
  };
  model_weights: Record<string, number>;
  regime: RegimeDetails;
  target_price_5d?: number;
  stop_loss?: number;
  take_profit?: number;
  prob_buy?: number;
  prob_sell?: number;
  max_loss_pct?: number;
  is_computed?: boolean;
  message?: string;
  model_status?: "trained" | "heuristic" | "fallback";
}

export interface ForecastPoint {
  target_date: string;
  horizon_days: number;
  predicted_price: number;
  predicted_direction: string;
  confidence: number;
  prediction_low: number;
  prediction_high: number;
  change_pct?: number;
}

export interface ModelForecast {
  model_name: string;
  forecasts: ForecastPoint[];
}

export interface ForecastResponse {
  symbol: string;
  current_price: number;
  generated_at: string;
  model_results: ModelForecast[];
  forecast?: ForecastPoint[];
}
