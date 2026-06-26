import type { SignalResponse, ForecastResponse } from "@/types/intelligence";
import { getApiV1Url } from "@/lib/runtime-config";

const API_URL = getApiV1Url();

type UnknownRecord = Record<string, unknown>;

function asNumber(value: unknown, fallback = 0): number {
  const numeric = typeof value === "number" ? value : typeof value === "string" ? Number(value) : NaN;
  return Number.isFinite(numeric) ? numeric : fallback;
}

function asDirection(value: unknown): SignalResponse["ensemble"]["direction"] {
  const normalized = String(value ?? "").toUpperCase();
  if (
    normalized === "STRONG_BUY" ||
    normalized === "BUY" ||
    normalized === "NEUTRAL" ||
    normalized === "SELL" ||
    normalized === "STRONG_SELL"
  ) {
    return normalized;
  }
  return "NEUTRAL";
}

function normalizeRegime(raw: unknown): SignalResponse["regime"] {
  const source = raw && typeof raw === "object" ? (raw as UnknownRecord) : {};
  const probsValue = source.probs;
  const transitionValue = source.transition_probs ?? source.transition_matrix;

  const probs = Array.isArray(probsValue)
    ? {
        bull: asNumber(probsValue[0]),
        bear: asNumber(probsValue[1]),
        sideways: asNumber(probsValue[2]),
        crisis: asNumber(probsValue[3]),
      }
    : probsValue && typeof probsValue === "object"
      ? {
          bull: asNumber((probsValue as UnknownRecord).bull),
          bear: asNumber((probsValue as UnknownRecord).bear),
          sideways: asNumber((probsValue as UnknownRecord).sideways),
          crisis: asNumber((probsValue as UnknownRecord).crisis),
        }
      : { bull: 0, bear: 0, sideways: 0, crisis: 0 };

  const transition_probs = Array.isArray(transitionValue)
    ? {
        bull: asNumber((transitionValue[0] as unknown[] | undefined)?.[0]),
        bear: asNumber((transitionValue[1] as unknown[] | undefined)?.[1]),
        sideways: asNumber((transitionValue[2] as unknown[] | undefined)?.[2]),
        crisis: asNumber((transitionValue[3] as unknown[] | undefined)?.[3]),
      }
    : transitionValue && typeof transitionValue === "object"
      ? {
          bull: asNumber((transitionValue as UnknownRecord).bull),
          bear: asNumber((transitionValue as UnknownRecord).bear),
          sideways: asNumber((transitionValue as UnknownRecord).sideways),
          crisis: asNumber((transitionValue as UnknownRecord).crisis),
        }
      : { bull: 0, bear: 0, sideways: 0, crisis: 0 };

  const state = String(source.state ?? "SIDEWAYS").toUpperCase();

  return {
    state:
      state === "BULL" || state === "BEAR" || state === "SIDEWAYS" || state === "CRISIS"
        ? state
        : "SIDEWAYS",
    probs,
    transition_probs,
  };
}

function normalizeSignalResponse(raw: UnknownRecord): SignalResponse {
  const ensembleRaw = raw.ensemble && typeof raw.ensemble === "object" ? (raw.ensemble as UnknownRecord) : {};
  const modelsRaw = raw.models && typeof raw.models === "object" ? (raw.models as UnknownRecord) : {};
  const tftRaw = modelsRaw.tft && typeof modelsRaw.tft === "object" ? (modelsRaw.tft as UnknownRecord) : {};
  const hmmRaw = modelsRaw.hmm_garch && typeof modelsRaw.hmm_garch === "object" ? (modelsRaw.hmm_garch as UnknownRecord) : {};
  const gnnRaw = modelsRaw.gnn && typeof modelsRaw.gnn === "object" ? (modelsRaw.gnn as UnknownRecord) : {};
  const lstmRaw = modelsRaw.lstm_attn && typeof modelsRaw.lstm_attn === "object" ? (modelsRaw.lstm_attn as UnknownRecord) : {};
  const xgboostRaw = modelsRaw.xgboost && typeof modelsRaw.xgboost === "object" ? (modelsRaw.xgboost as UnknownRecord) : {};
  const techRaw = modelsRaw.technical && typeof modelsRaw.technical === "object" ? (modelsRaw.technical as UnknownRecord) : {};
  const patRaw = modelsRaw.pattern && typeof modelsRaw.pattern === "object" ? (modelsRaw.pattern as UnknownRecord) : {};
  const momRaw = modelsRaw.momentum && typeof modelsRaw.momentum === "object" ? (modelsRaw.momentum as UnknownRecord) : {};
  const regRaw = modelsRaw.regime && typeof modelsRaw.regime === "object" ? (modelsRaw.regime as UnknownRecord) : {};
  const weightsRaw = raw.model_weights && typeof raw.model_weights === "object" ? (raw.model_weights as UnknownRecord) : {};

  return {
    symbol: String(raw.symbol ?? "UNKNOWN"),
    timestamp: String(raw.timestamp ?? new Date().toISOString()),
    ensemble: {
      signal: asDirection(ensembleRaw.direction ?? ensembleRaw.signal),
      direction: asDirection(ensembleRaw.direction),
      confidence: asNumber(ensembleRaw.confidence),
      kelly_fraction: asNumber(ensembleRaw.kelly_fraction),
    },
    models: {
      tft: {
        p10: asNumber(tftRaw.p10 ?? tftRaw.p10_return),
        p50: asNumber(tftRaw.p50 ?? tftRaw.p50_return),
        p90: asNumber(tftRaw.p90 ?? tftRaw.p90_return),
        raw_signal: asNumber(tftRaw.raw_signal),
        horizon_days: Math.round(asNumber(tftRaw.horizon_days, 1)),
      },
      hmm_garch: {
        regime_signal: String(hmmRaw.regime_signal ?? ""),
        vol_forecast_1d: asNumber(hmmRaw.vol_forecast_1d),
        vol_forecast_21d: asNumber(hmmRaw.vol_forecast_21d),
      },
      gnn: {
        spillover_risk: asNumber(gnnRaw.spillover_risk),
        embedding_norm: asNumber(gnnRaw.embedding_norm),
        top_correlated_assets: Array.isArray(gnnRaw.top_correlated_assets)
          ? gnnRaw.top_correlated_assets.map((item) => String(item))
          : [],
      },
      lstm_attn: {
        raw_signal: asNumber(lstmRaw.raw_signal),
        attention_peaks: Array.isArray(lstmRaw.attention_peaks)
          ? lstmRaw.attention_peaks.map((item) =>
              item && typeof item === "object" ? (item as Record<string, number>) : {}
            )
          : [],
      },
      xgboost: {
        raw_signal: asNumber(xgboostRaw.raw_signal),
        top_features: Array.isArray(xgboostRaw.top_features)
          ? xgboostRaw.top_features.map((item) =>
              item && typeof item === "object" ? (item as Record<string, string | number>) : {}
            )
          : [],
      },
      technical: {
        score: asNumber(techRaw.score),
        rsi: asNumber(techRaw.rsi),
        macd_histogram: asNumber(techRaw.macd_histogram),
        bb_position: asNumber(techRaw.bb_position),
        adx: asNumber(techRaw.adx),
        supertrend_direction: asNumber(techRaw.supertrend_direction),
        above_vwap: Boolean(techRaw.above_vwap),
        indicators_computed: asNumber(techRaw.indicators_computed),
      },
      pattern: {
        pattern_score: asNumber(patRaw.pattern_score),
        patterns_detected: Array.isArray(patRaw.patterns_detected) ? patRaw.patterns_detected : [],
        bullish_count: asNumber(patRaw.bullish_count),
        bearish_count: asNumber(patRaw.bearish_count),
      },
      momentum: {
        momentum_score: asNumber(momRaw.momentum_score),
        ret_1d: asNumber(momRaw.ret_1d),
        ret_5d: asNumber(momRaw.ret_5d),
        ret_21d: asNumber(momRaw.ret_21d),
        jt_momentum: asNumber(momRaw.jt_momentum),
        vol_21d: asNumber(momRaw.vol_21d),
        yang_zhang_vol: asNumber(momRaw.yang_zhang_vol),
        dist_52w_high: asNumber(momRaw.dist_52w_high),
        dist_52w_low: asNumber(momRaw.dist_52w_low),
      },
      regime: {
        regime: String(regRaw.regime ?? ""),
        bull_prob: asNumber(regRaw.bull_prob),
        bear_prob: asNumber(regRaw.bear_prob),
        regime_confidence: asNumber(regRaw.regime_confidence),
        hmm_used: Boolean(regRaw.hmm_used),
      },
    },
    model_weights: Object.fromEntries(
      Object.entries(weightsRaw).map(([key, value]) => [key, asNumber(value)])
    ),
    regime: normalizeRegime(raw.regime),
    target_price_5d: asNumber(raw.target_price_5d),
    stop_loss: asNumber(raw.stop_loss),
    take_profit: asNumber(raw.take_profit),
    prob_buy: asNumber(raw.prob_buy),
    prob_sell: asNumber(raw.prob_sell),
    max_loss_pct: asNumber(raw.max_loss_pct),
    is_computed: Boolean(raw.is_computed),
    message: String(raw.message ?? ""),
  };
}

const parseJson = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
};

export const intelligenceApi = {
  async getSignal(symbol: string): Promise<SignalResponse> {
    const response = await fetch(`${API_URL}/signals/${encodeURIComponent(symbol)}`, {
      method: "GET",
      cache: "no-store",
    });
    return parseJson<UnknownRecord>(response).then(normalizeSignalResponse);
  },

  async getBulkSignals(symbols: string[]): Promise<SignalResponse[]> {
    const params = new URLSearchParams({ symbols: symbols.join(",") });
    const response = await fetch(`${API_URL}/signals/bulk?${params.toString()}`, {
      method: "GET",
      cache: "no-store",
    });
    return parseJson<UnknownRecord[] | { signals?: UnknownRecord[] }>(response).then((data) => {
      const items = Array.isArray(data)
        ? data
        : Array.isArray(data.signals)
          ? data.signals
          : [];
      return items.map(normalizeSignalResponse);
    });
  },

  async getForecast(symbol: string, horizons: number[] = [1, 5, 10, 15, 20, 25, 30]): Promise<ForecastResponse> {
    const response = await fetch(`${API_URL}/predictions/forecast`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ symbol, horizons }),
      cache: "no-store",
    });
    return parseJson<ForecastResponse>(response);
  },
};
