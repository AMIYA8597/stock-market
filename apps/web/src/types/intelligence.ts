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
  };
  model_weights: Record<string, number>;
  regime: RegimeDetails;
}
