import type { SignalResponse, ForecastResponse, ForecastPoint } from "@/types/intelligence";

export const ALL_FORECAST_HORIZONS = [
  "1m", "2m", "3m", "5m", "10m", "15m", "30m", "1h", "1d", "1w", "15d", "1mo", "1y",
] as const;
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
  const modelsRaw = (raw.models && typeof raw.models === "object" ? raw.models : ensembleRaw) as UnknownRecord;
  const tftRaw = modelsRaw.tft && typeof modelsRaw.tft === "object" ? (modelsRaw.tft as UnknownRecord) : {};
  const hmmRaw = modelsRaw.hmm_garch && typeof modelsRaw.hmm_garch === "object" ? (modelsRaw.hmm_garch as UnknownRecord) : {};
  const gnnRaw = modelsRaw.gnn && typeof modelsRaw.gnn === "object" ? (modelsRaw.gnn as UnknownRecord) : {};
  const lstmRaw = modelsRaw.lstm_attn && typeof modelsRaw.lstm_attn === "object" ? (modelsRaw.lstm_attn as UnknownRecord) : {};
  const xgboostRaw = modelsRaw.xgboost && typeof modelsRaw.xgboost === "object" ? (modelsRaw.xgboost as UnknownRecord) : {};
  const techRaw = modelsRaw.technical && typeof modelsRaw.technical === "object" ? (modelsRaw.technical as UnknownRecord) : {};
  const patRaw = modelsRaw.pattern && typeof modelsRaw.pattern === "object" ? (modelsRaw.pattern as UnknownRecord) : {};
  const momRaw = modelsRaw.momentum && typeof modelsRaw.momentum === "object" ? (modelsRaw.momentum as UnknownRecord) : {};
  const regRaw = modelsRaw.regime && typeof modelsRaw.regime === "object" ? (modelsRaw.regime as UnknownRecord) : {};
  const weightsRaw = (raw.model_weights ?? ensembleRaw.model_weights) && typeof (raw.model_weights ?? ensembleRaw.model_weights) === "object" ? ((raw.model_weights ?? ensembleRaw.model_weights) as UnknownRecord) : {};

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
    regime: normalizeRegime(raw.regime ?? ensembleRaw.regime),
    target_price_5d: asNumber(raw.target_price_5d ?? ensembleRaw.target_price_5d),
    stop_loss: asNumber(raw.stop_loss ?? ensembleRaw.stop_loss),
    take_profit: asNumber(raw.take_profit ?? ensembleRaw.take_profit),
    prob_buy: asNumber(raw.prob_buy ?? ensembleRaw.prob_buy),
    prob_sell: asNumber(raw.prob_sell ?? ensembleRaw.prob_sell),
    max_loss_pct: asNumber(raw.max_loss_pct ?? ensembleRaw.max_loss_pct),
    is_computed: Boolean(raw.is_computed),
    message: String(raw.message ?? ""),
    model_status: (raw.model_status as "trained" | "heuristic" | "fallback" | undefined) ?? ensembleRaw.model_status as "trained" | "heuristic" | "fallback",
    model_version: raw.model_version ? String(raw.model_version) : undefined,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    forecast: Array.isArray(raw.forecast) ? raw.forecast as any[] : undefined,
  };
}

const parseJson = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
};

// The technical signals endpoint (/signals/{symbol}) returns a flatter shape than the
// ML ensemble endpoint (/predictions/{symbol}) — adapt it into the shape
// normalizeSignalResponse expects so it can still populate ensemble.direction/confidence.
function adaptTechnicalSignalToRaw(raw: UnknownRecord): UnknownRecord {
  return {
    symbol: raw.symbol,
    timestamp: raw.timestamp,
    ensemble: {
      direction: raw.direction,
      confidence: raw.confidence,
      kelly_fraction: 0,
    },
    model_status: "heuristic",
    message: "ML ensemble prediction unavailable; showing technical signal instead.",
  };
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {};
  const { createClient } = await import("@/lib/supabase/client");
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    return { Authorization: `Bearer ${session.access_token}` };
  }
  return {};
}

async function fetchSignalWithFallback(symbol: string): Promise<UnknownRecord> {
  const authHeaders = await getAuthHeaders();
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);
    const response = await fetch(`${API_URL}/predictions/${encodeURIComponent(symbol)}`, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
      headers: { ...authHeaders },
    }).finally(() => clearTimeout(timeoutId));
    return await parseJson<UnknownRecord>(response);
  } catch {
    const response = await fetch(`${API_URL}/signals/${encodeURIComponent(symbol)}`, {
      method: "GET",
      cache: "no-store",
      headers: { ...authHeaders },
    });
    const raw = await parseJson<UnknownRecord>(response);
    return adaptTechnicalSignalToRaw(raw);
  }
}

export const intelligenceApi = {
  async getSignal(symbol: string): Promise<SignalResponse> {
    const raw = await fetchSignalWithFallback(symbol);
    return normalizeSignalResponse(raw);
  },

  async getBulkSignals(symbols: string[]): Promise<SignalResponse[]> {
    if (symbols.length === 0) return [];
    const authHeaders = await getAuthHeaders();
    // Use the bulk endpoint instead of firing 50 individual requests
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 15000);
      const response = await fetch(
        `${API_URL}/signals/bulk?symbols=${encodeURIComponent(symbols.join(","))}`,
        {
          method: "GET",
          cache: "no-store",
          signal: controller.signal,
          headers: { ...authHeaders },
        },
      ).finally(() => clearTimeout(timeoutId));
      const raw = await parseJson<UnknownRecord>(response);
      // The bulk endpoint returns { signals: [...] } or an array directly
      const signalArray = Array.isArray(raw) ? raw : Array.isArray((raw as any).signals) ? (raw as any).signals : [];
      return signalArray.map((s: UnknownRecord) => normalizeSignalResponse(s));
    } catch (err) {
      console.warn("Bulk signals endpoint failed, falling back to individual calls:", err);
      // Fallback: fetch individually with limited concurrency
      const CONCURRENCY = 5;
      const all: SignalResponse[] = [];
      for (let i = 0; i < symbols.length; i += CONCURRENCY) {
        const batch = symbols.slice(i, i + CONCURRENCY);
        const results = await Promise.allSettled(batch.map(fetchSignalWithFallback));
        for (const res of results) {
          if (res.status === "fulfilled") {
            all.push(normalizeSignalResponse(res.value));
          }
        }
      }
      return all;
    }
  },

  async getForecast(symbol: string, horizons: number[] = [1, 5, 10, 15, 20, 25, 30]): Promise<ForecastResponse> {
    const authHeaders = await getAuthHeaders();
    const response = await fetch(`${API_URL}/predictions/forecast`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
      },
      body: JSON.stringify({ symbol, horizons }),
      cache: "no-store",
    });
    return parseJson<ForecastResponse>(response);
  },

  /** Real SARIMAX multi-horizon forecast (1m through 1y) — independent of
   * whether an XGBoost model is trained for this symbol, since it's pure
   * statistical forecasting on price history. See HORIZON_SPECS on the
   * backend for exactly what data window backs each horizon. */
  async getMultiHorizonForecast(
    symbol: string,
    horizons: readonly string[] = ALL_FORECAST_HORIZONS
  ): Promise<ForecastPoint[]> {
    const authHeaders = await getAuthHeaders();
    const response = await fetch(`${API_URL}/predictions/forecast`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders },
      body: JSON.stringify({ symbol, horizons }),
      cache: "no-store",
    });
    const data = await parseJson<{
      symbol: string;
      generated_at: string;
      horizons: Record<
        string,
        {
          status: "ok" | "error";
          message?: string;
          predicted_price?: number;
          prediction_low?: number;
          prediction_high?: number;
          change_pct?: number;
          confidence?: "experimental" | "low" | "medium" | "high";
          data_window?: string;
        }
      >;
    }>(response);

    const points: ForecastPoint[] = [];
    for (const [horizon, v] of Object.entries(data.horizons)) {
      if (v.status !== "ok" || v.predicted_price === undefined) continue;
      points.push({
        target_date: data.generated_at,
        horizon,
        predicted_price: v.predicted_price,
        predicted_direction: (v.change_pct ?? 0) >= 0 ? "BUY" : "SELL",
        confidence_label: v.confidence ?? "low",
        data_window: v.data_window ?? "",
        prediction_low: v.prediction_low ?? v.predicted_price,
        prediction_high: v.prediction_high ?? v.predicted_price,
        change_pct: v.change_pct ?? 0,
      });
    }
    return points;
  },
};
