/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
import type {
  TokenResponse,
  UserProfile,
  Quote,
  HistoryResponse,
  ScreenerFilter,
  ScreenerResponse,
  Prediction,
  ModelEnsemble,
  Portfolio,
  RiskMetrics,
  OptimizeRequest,
  OptimizeResponse,
  BacktestConfig,
  BacktestResult,
  AlertDefinition,
  AlertEvent,
  ResearchReport,
  RegimeData,
  CorrelationNode,
  CorrelationEdge,
  SignalResponse,
  SearchResponse,
  UniverseResponse,
} from "@neuroquant/types";
import { getApiBaseUrl } from "@/lib/runtime-config";
import { createClient } from './supabase/client';
import { z } from "zod";

const API_BASE = getApiBaseUrl();
const API_PREFIX = "/api/v1";

type UnknownRecord = Record<string, unknown>;

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body: unknown
  ) {
    const bodyObj = body as Record<string, any>;
    const detailMessage = bodyObj?.error?.message || bodyObj?.detail?.message || bodyObj?.detail || statusText;
    super(typeof detailMessage === "string" ? detailMessage : `API Error ${status}: ${statusText}`);
    this.name = "ApiError";
  }
}

let _cachedSessionToken: { token: string | undefined; expiresAt: number } = { token: undefined, expiresAt: 0 };

export async function fetchApi<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${API_PREFIX}${path}`;
  
  let token: string | undefined;
  const now = Date.now();
  if (_cachedSessionToken.token && now < _cachedSessionToken.expiresAt) {
    token = _cachedSessionToken.token;
  } else {
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      token = session?.access_token;
      _cachedSessionToken = { token, expiresAt: now + 10_000 };
    } catch {
      token = undefined;
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  const abortFromCaller = () => controller.abort();
  options.signal?.addEventListener("abort", abortFromCaller, { once: true });

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new ApiError(408, "Request Timeout", {
        detail: `The request to ${path} timed out after 15 seconds`,
      });
    }
    throw error;
  } finally {
    clearTimeout(timeout);
    options.signal?.removeEventListener("abort", abortFromCaller);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, response.statusText, body);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

// ─── Auth ────────────────────────────────────────────

export const authApi = {
  getProfile(): Promise<UserProfile> {
    return fetchApi("/users/profile");
  },
  // Three possible 201 bodies:
  //  - TokenResponse: auto-verified and signed in (no SendGrid configured)
  //  - { login_required: true }: account created, auto sign-in failed -> go to login
  //  - { email, message }: OTP sent, verify on the register page
  register(data: { email: string; password: string; full_name?: string }): Promise<
    | TokenResponse
    | { status: "created"; login_required: true; message: string }
    | { email: string; message: string }
  > {
    return fetchApi("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
  checkEmail(email: string): Promise<{ exists: boolean }> {
    return fetchApi("/auth/check-email", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },
  login(data: { email: string; password: string }): Promise<TokenResponse> {
    return fetchApi("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
  verifySignupOtp(data: { email: string; otp: string; password: string }): Promise<TokenResponse> {
    return fetchApi("/auth/verify-signup-otp", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
  resendOtp(data: { email: string; purpose: "signup" | "password_reset" }): Promise<{ message: string }> {
    return fetchApi("/auth/resend-otp", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
  forgotPassword(email: string): Promise<{ message: string }> {
    return fetchApi("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },
  resetPassword(data: { email: string; otp: string; new_password: string }): Promise<{ message: string }> {
    return fetchApi("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};

export const usersApi = {
  getProfile(): Promise<{ id: string; email: string; full_name: string | null; role: string; is_active: boolean }> {
    return fetchApi("/users/profile");
  },
  updateProfile(full_name: string): Promise<{ id: string; email: string; full_name: string | null; role: string; is_active: boolean }> {
    return fetchApi("/users/profile", {
      method: "PATCH",
      body: JSON.stringify({ full_name }),
    });
  },
};

export const adminApi = {
  listUsers(): Promise<Array<{ id: string; email: string; full_name: string | null; role: string; is_active: boolean }>> {
    return fetchApi("/admin/users");
  },
  updateUserRole(userId: string, role: "USER" | "ADMIN"): Promise<{ id: string; email: string; full_name: string | null; role: string; is_active: boolean }> {
    return fetchApi(`/admin/users/${encodeURIComponent(userId)}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    });
  },
  getContent(): Promise<{ posts: Array<{ id: string; slug: string; title: string; status: string }> }> {
    return fetchApi("/admin/content");
  },
};

export const blogApi = {
  listPosts(limit = 20): Promise<{ items: Array<{ slug: string; title: string; excerpt: string; published_at: string | null }> }> {
    return fetchApi(`/blog/posts?limit=${limit}`);
  },
  getPost(slug: string): Promise<{ slug: string; title: string; excerpt: string; content: string; status: string; published_at: string | null }> {
    return fetchApi(`/blog/posts/${encodeURIComponent(slug)}`);
  },
};

export const notificationsApi = {
  list(): Promise<{ items: Array<{ id: string; title: string; message: string; level: string; is_read: boolean; created_at: string }> }> {
    return fetchApi("/notifications");
  },
  markRead(notificationId: string): Promise<{ status: string }> {
    return fetchApi(`/notifications/${encodeURIComponent(notificationId)}/read`, { method: "POST" });
  },
};

export const paymentsApi = {
  getPlans(): Promise<{ items: Array<{ id: string; name: string; description: string; price_inr: string; features: string[] }> }> {
    return fetchApi("/payments/plans");
  },
  async createIntent(data: { plan_id: string }): Promise<{ intent_id: string; provider_order_id: string; status: string; is_test_mode: boolean }> {
    const idem = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `idem-${Date.now()}`;
    return fetchApi("/payments/intents", {
      method: "POST",
      headers: { "Idempotency-Key": idem },
      body: JSON.stringify(data),
    });
  },
  confirmIntent(intent_id: string, razorpay_payment_id: string, razorpay_signature?: string): Promise<{ intent_id: string; status: string; completed_at: string | null }> {
    return fetchApi("/payments/confirm", {
      method: "POST",
      body: JSON.stringify({ intent_id, razorpay_payment_id, razorpay_signature }),
    });
  },
  getSubscription(): Promise<{ id: string; status: string; plan_name: string; current_period_end: string | null; cancel_at_period_end: boolean } | null> {
    return fetchApi("/payments/subscription");
  },
  cancelSubscription(): Promise<{ status: string; current_period_end: string | null }> {
    return fetchApi("/payments/cancel-subscription", {
      method: "POST"
    });
  },
};

// ─── Market Data ────────────────────────────────────

const normalizeInterval = (interval: string): string => {
  const map: Record<string, string> = {
    "1M": "1m",
    "3M": "3m",
    "5M": "5m",
    "10M": "10m",
    "15M": "15m",
    "30M": "30m",
    "45M": "45m",
    "1H": "1h",
    "2H": "2h",
    "4H": "4h",
    "1D": "1d",
    "1W": "1w",
    "1MO": "1mo",
  };
  const upper = interval.toUpperCase();
  return map[upper] ?? interval.toLowerCase();
};

const numberOrNull = z.preprocess((val) => {
  if (typeof val === 'number') return val;
  if (typeof val === 'string' && val.trim() !== '') {
    const parsed = Number(val);
    if (!isNaN(parsed)) return parsed;
  }
  return null;
}, z.number().nullable());

const mapQuote = (raw: UnknownRecord): Quote => {
  const price = numberOrNull.parse(raw.price);
  const change = numberOrNull.parse(raw.change);
  const changePct = numberOrNull.parse(raw.change_percent !== undefined ? raw.change_percent : raw.change_pct);
  const symbol = typeof raw.symbol === "string" ? raw.symbol : typeof raw.ticker === "string" ? raw.ticker : "UNKNOWN";

  return {
    symbol,
    price: price as any,
    change: change as any,
    change_percent: changePct as any,
    volume: numberOrNull.parse(raw.volume) as any,
    high: numberOrNull.parse(raw.high !== undefined ? raw.high : raw.high_52w) ?? (price as any),
    low: numberOrNull.parse(raw.low !== undefined ? raw.low : raw.low_52w) ?? (price as any),
    open: numberOrNull.parse(raw.open) ?? ((price && change) ? price - change : null) as any,
    previous_close: numberOrNull.parse(raw.previous_close) ?? ((price && change) ? price - change : null) as any,
    timestamp: typeof raw.timestamp === "string" ? raw.timestamp : new Date().toISOString(),
    source: typeof raw.source === "string" ? raw.source : undefined,
  };
};

const mapHistory = (raw: UnknownRecord): HistoryResponse => {
  const rawBars = Array.isArray(raw.bars)
    ? (raw.bars as UnknownRecord[])
    : Array.isArray(raw.data)
      ? (raw.data as UnknownRecord[])
      : [];

  const validBars = rawBars.map((bar) => {
    let timestamp = "";
    if (typeof bar.timestamp === "string") {
      timestamp = bar.timestamp;
    } else if (typeof bar.time === "string") {
      timestamp = bar.time;
    } else if (typeof bar.time === "number") {
      timestamp = new Date(bar.time * 1000).toISOString();
    } else if (typeof bar.timestamp === "number") {
      timestamp = new Date(bar.timestamp * 1000).toISOString();
    }

    const tsNum = new Date(timestamp).getTime();
    if (isNaN(tsNum)) return null;

    return {
      timestamp,
      _tsNum: tsNum, // temporary numeric value for sorting and deduplication
      open: numberOrNull.parse(bar.open) as any,
      high: numberOrNull.parse(bar.high) as any,
      low: numberOrNull.parse(bar.low) as any,
      close: numberOrNull.parse(bar.close) as any,
      volume: numberOrNull.parse(bar.volume) as any,
      adjusted_close: bar.adjusted_close !== undefined && bar.adjusted_close !== null
        ? numberOrNull.parse(bar.adjusted_close) as any
        : undefined,
    };
  }).filter((b) => b !== null);

  // Sort ascending by time
  validBars.sort((a, b) => (a as any)._tsNum - (b as any)._tsNum);

  // De-duplicate exactly identical timestamps (last one wins)
  const dedupedMap = new Map();
  for (const b of validBars) {
    dedupedMap.set((b as any)._tsNum, b);
  }
  
  const finalBars = Array.from(dedupedMap.values()).map(({ _tsNum, ...rest }: any) => rest);

  return {
    symbol: typeof raw.symbol === "string" ? raw.symbol : "UNKNOWN",
    interval: typeof raw.interval === "string" ? raw.interval : "1d",
    bars: finalBars,
    count: (numberOrNull.parse(raw.count) ?? finalBars.length) as any,
    source: typeof raw.source === "string" ? raw.source : undefined,
  };
};

export const marketApi = {
  getQuote(symbol: string): Promise<Quote> {
    return fetchApi<UnknownRecord>(`/market/quote/${encodeURIComponent(symbol)}`).then(
      mapQuote
    );
  },
  getZones(symbol: string): Promise<any> {
    return fetchApi(`/market/zones/${encodeURIComponent(symbol)}`);
  },
  getPatterns(symbol: string): Promise<any> {
    return fetchApi(`/market/patterns/${encodeURIComponent(symbol)}`);
  },

  getHistory(
    symbol: string,
    interval: string = "1D",
    start?: string,
    end?: string,
    period?: string
  ): Promise<HistoryResponse> {
    const normalizedInterval = normalizeInterval(interval);
    const params = new URLSearchParams({ interval: normalizedInterval });
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    if (period) params.set("period", period);
    return fetchApi<UnknownRecord>(
      `/market/history/${encodeURIComponent(symbol)}?${params.toString()}`
    ).then(mapHistory);
  },

  async getQuotes(symbols: string[]): Promise<Quote[]> {
    if (!symbols.length) return [];
    try {
      const res = await fetchApi<unknown>(
        `/market/quotes?symbols=${encodeURIComponent(symbols.join(","))}`
      );
      if (Array.isArray(res)) {
        return res.map((q) => mapQuote(q as UnknownRecord));
      }
      if (res && typeof res === "object") {
        const obj = res as Record<string, unknown>;
        if (Array.isArray(obj.quotes)) {
          return obj.quotes.map((q) => mapQuote(q as UnknownRecord));
        }
        return Object.values(obj).map((q) => mapQuote(q as UnknownRecord));
      }
    } catch {
      // Fallback to individual fetches if batch query fails
    }
    const settled = await Promise.allSettled(
      symbols.map((symbol) => marketApi.getQuote(symbol))
    );
    return settled
      .filter((result): result is PromiseFulfilledResult<Quote> => result.status === "fulfilled")
      .map((result) => result.value);
  },

  getUniverse(): Promise<UniverseResponse> {
    return fetchApi<UniverseResponse>("/market/universe");
  },

  getStatus(): Promise<{ market_open: boolean; next_open: string; next_close: string | null }> {
    return fetchApi<{ market_open: boolean; next_open: string; next_close: string | null }>("/market/status");
  },

  search(query: string): Promise<SearchResponse> {
    return fetchApi<SearchResponse>(`/market/search?q=${encodeURIComponent(query)}`);
  },
};

// ─── Screener ───────────────────────────────────────

export const screenerApi = {
  search(filters: Partial<ScreenerFilter>): Promise<ScreenerResponse> {
    const cleanFilters: Record<string, unknown> = {};
    if (filters.asset_class !== undefined) cleanFilters.asset_class = filters.asset_class;
    if (filters.exchange !== undefined) cleanFilters.exchange = filters.exchange;
    if (filters.min_market_cap !== undefined) cleanFilters.min_market_cap = filters.min_market_cap;
    if (filters.max_market_cap !== undefined) cleanFilters.max_market_cap = filters.max_market_cap;
    if (filters.rsi_min !== undefined) cleanFilters.rsi_min = filters.rsi_min;
    if (filters.rsi_max !== undefined) cleanFilters.rsi_max = filters.rsi_max;
    if (filters.above_sma_200 !== undefined) cleanFilters.above_sma_200 = filters.above_sma_200;
    if (filters.volume_surge !== undefined) cleanFilters.volume_surge = filters.volume_surge;
    if (filters.ml_confidence_min !== undefined) cleanFilters.ml_confidence_min = filters.ml_confidence_min;

    const payload = {
      exchange: [filters.exchange ?? "NSE"],
      filters: cleanFilters,
      sort_by: filters.sort_by ?? "sharpe_21d",
      limit: filters.limit ?? 50,
    };

    return fetchApi<UnknownRecord>("/screener/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }).then((raw) => {
      const rawResults = Array.isArray(raw.results)
        ? (raw.results as UnknownRecord[])
        : [];

      const results = rawResults.map((item) => {
        const symbol =
          typeof item.ticker === "string"
            ? item.ticker
            : typeof item.symbol === "string"
              ? item.symbol
              : "UNKNOWN";

        const price = numberOrNull.parse(item.price);
        const changePercent = numberOrNull.parse(item.change_pct ?? item.change_percent ?? item.sharpe_21d);
        const volume = numberOrNull.parse(item.volume ?? item.volume_ratio);
        const marketCap = numberOrNull.parse(item.market_cap);
        const rsi = numberOrNull.parse(item.rsi);
        const mlSignal = typeof item.signal_direction === "string" ? item.signal_direction : typeof item.signal === "string" ? item.signal : null;
        const mlConfidence = numberOrNull.parse(item.signal_confidence ?? item.ml_confidence);

        return {
          symbol,
          name: typeof item.name === "string" ? item.name : symbol,
          asset_class: typeof item.asset_type === "string" ? item.asset_type : "equity",
          exchange: typeof item.exchange === "string" ? item.exchange : "NSE",
          sector: typeof item.sector === "string" ? item.sector : null,
          price: price as any,
          change_percent: changePercent as any,
          volume: volume as any,
          market_cap: marketCap as any,
          rsi: rsi as any,
          ml_signal: mlSignal,
          ml_confidence: mlConfidence as any,
        };
      });

      const total =
        typeof raw.total_matched === "number"
          ? raw.total_matched
          : results.length;

      return {
        results,
        total,
        limit: payload.limit,
        offset: filters.offset ?? 0,
      };
    });
  },

  getPresets(): Promise<Array<{ name: string; description: string; filters_json: Record<string, unknown> }>> {
    return fetchApi<Array<{ name: string; description: string; filters_json: Record<string, unknown> }>>("/screener/presets");
  },
};

// ─── Predictions ────────────────────────────────────

export const predictionsApi = {
  getLatest(symbol: string): Promise<Prediction> {
    return fetchApi(`/predictions/latest/${encodeURIComponent(symbol)}`);
  },

  getEnsemble(symbol: string): Promise<ModelEnsemble> {
    return fetchApi(`/predictions/ensemble/${encodeURIComponent(symbol)}`);
  },

  getHistory(
    symbol: string,
    model?: string
  ): Promise<Prediction[]> {
    const params = model ? `?model=${encodeURIComponent(model)}` : "";
    return fetchApi(
      `/predictions/history/${encodeURIComponent(symbol)}${params}`
    );
  },
};

// ─── Portfolio ──────────────────────────────────────

export const portfolioApi = {
  list(): Promise<Portfolio[]> {
    return fetchApi("/portfolio");
  },

  get(id: number): Promise<Portfolio> {
    return fetchApi(`/portfolio/${id}`);
  },

  getPerformance(): Promise<{series: any[], start_date: string, end_date: string, total_return: number, benchmark_return: number, excess_return: number}> {
    return fetchApi("/portfolio/performance");
  },


  create(data: {
    name: string;
    description?: string;
    initial_capital?: number;
  }): Promise<Portfolio> {
    return fetchApi("/portfolio", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  addHolding(
    portfolioId: number,
    data: { symbol: string; quantity: number; avg_cost: number }
  ): Promise<Portfolio> {
    return fetchApi(`/portfolio/${portfolioId}/holdings`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  getRisk(portfolioId: number): Promise<RiskMetrics> {
    return fetchApi(`/portfolio/${portfolioId}/risk-metrics`);
  },

  optimize(data: OptimizeRequest): Promise<OptimizeResponse> {
    return fetchApi("/portfolio/optimize", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};

// ─── Backtesting ────────────────────────────────────

export const backtestApi = {
  run(config: BacktestConfig): Promise<BacktestResult> {
    return fetchApi("/backtest/run", {
      method: "POST",
      body: JSON.stringify(config),
    });
  },
};

// ─── Alerts ─────────────────────────────────────────

export const alertsApi = {
  list(): Promise<AlertDefinition[]> {
    return fetchApi<{ alerts: UnknownRecord[]; total_count: number }>("/alerts").then((res) =>
      (res.alerts ?? []).map((raw, index) => {
        const symbol =
          typeof raw.symbol === "string" ? raw.symbol : null;
        const alertTypeRaw =
          typeof raw.alert_type === "string" ? raw.alert_type.toLowerCase() : "price";
        const normalizedType: AlertDefinition["alert_type"] =
          alertTypeRaw === "technical" ||
          alertTypeRaw === "ml_signal" ||
          alertTypeRaw === "sentiment" ||
          alertTypeRaw === "anomaly" ||
          alertTypeRaw === "news"
            ? alertTypeRaw
            : "price";

        return {
          id: typeof raw.id === "string" ? raw.id : `alert-${index + 1}`,
          name: typeof raw.name === "string" ? raw.name : `${symbol ?? "MARKET"} ${normalizedType}`,
          symbol,
          alert_type: normalizedType,
          conditions:
            raw.conditions && typeof raw.conditions === "object"
              ? (raw.conditions as Record<string, unknown>)
              : {},
          channels: ["in_app"],
          cooldown_minutes:
            typeof raw.cooldown_minutes === "number" ? raw.cooldown_minutes : 15,
          is_active: typeof raw.is_active === "boolean" ? raw.is_active : true,
          times_triggered:
            typeof raw.times_triggered === "number" ? raw.times_triggered : 0,
          last_triggered_at:
            typeof raw.last_triggered_at === "string" ? raw.last_triggered_at : null,
          created_at:
            typeof raw.created_at === "string" ? raw.created_at : new Date().toISOString(),
        };
      })
    );
  },

  create(data: Omit<AlertDefinition, "id" | "times_triggered" | "last_triggered_at" | "created_at">): Promise<AlertDefinition> {
    // Map frontend AlertDefinition to backend AlertCreateRequest
    const backendPayload = {
      symbol: data.symbol,
      alert_type: data.alert_type === "technical" ? "RSI_OB" : data.alert_type === "ml_signal" ? "SIGNAL_CHANGE" : "PRICE_ABOVE",
      threshold: (data.conditions as any)?.threshold ?? (data.conditions as any)?.value ?? 0,
      name: data.name,
      enabled: data.is_active ?? true,
    };
    
    return fetchApi("/alerts", {
      method: "POST",
      body: JSON.stringify(backendPayload),
    });
  },

  update(
    id: string,
    data: Partial<AlertDefinition>
  ): Promise<AlertDefinition> {
    const backendPayload: any = { ...data };
    if (data.is_active !== undefined) {
      backendPayload.enabled = data.is_active;
      delete backendPayload.is_active;
    }
    return fetchApi(`/alerts/${id}`, {
      method: "PATCH",
      body: JSON.stringify(backendPayload),
    });
  },

  delete(id: string): Promise<void> {
    return fetchApi(`/alerts/${id}`, { method: "DELETE" });
  },

  getHistory(limit?: number): Promise<AlertEvent[]> {
    const params = limit ? `?limit=${limit}` : "";
    return fetchApi<UnknownRecord[]>(`/alerts/history${params}`).then((rawItems) =>
      rawItems.map((raw, index) => {
        const alertTypeRaw =
          typeof raw.alert_type === "string" ? raw.alert_type.toLowerCase() : "price";
        const normalizedType: AlertEvent["alert_type"] =
          alertTypeRaw === "technical" ||
          alertTypeRaw === "ml_signal" ||
          alertTypeRaw === "sentiment" ||
          alertTypeRaw === "anomaly" ||
          alertTypeRaw === "news"
            ? alertTypeRaw
            : "price";

        const severityRaw = typeof raw.severity === "number" ? raw.severity : 2;
        const severity = Math.max(1, Math.min(5, Math.round(severityRaw))) as AlertEvent["severity"];

        return {
          id: typeof raw.id === "string" ? raw.id : `event-${index + 1}`,
          alert_id:
            typeof raw.alert_id === "string" ? raw.alert_id : `alert-${index + 1}`,
          alert_name:
            typeof raw.alert_name === "string" ? raw.alert_name : "Market Alert",
          symbol:
            typeof raw.symbol === "string" ? raw.symbol : "NIFTY50",
          alert_type: normalizedType,
          severity,
          message:
            typeof raw.message === "string"
              ? raw.message
              : "Alert triggered.",
          payload:
            raw.payload && typeof raw.payload === "object"
              ? (raw.payload as Record<string, unknown>)
              : {},
          triggered_at:
            typeof raw.triggered_at === "string"
              ? raw.triggered_at
              : new Date().toISOString(),
        };
      })
    );
  },
};

// ─── Research ───────────────────────────────────────

export const researchApi = {
  generateReport(symbol: string): Promise<ResearchReport> {
    return fetchApi(`/research/factor-exposure?symbol=${encodeURIComponent(symbol)}`);
  },

  getRegime(): Promise<RegimeData> {
    return fetchApi(`/regime/current`);
  },

  getCorrelationGraph(): Promise<{
    nodes: CorrelationNode[];
    edges: CorrelationEdge[];
  }> {
    return fetchApi("/research/correlation-graph");
  },
};

export const tradingApi = {
  getMode(): Promise<{ mode: string; is_live: boolean }> {
    return fetchApi("/trading/mode");
  },

  triggerKillSwitch(): Promise<unknown> {
    return fetchApi("/trading/kill-switch", {
      method: "POST",
    });
  },

  getAuditLog(limit = 50): Promise<{ logs: string[] }> {
    return fetchApi(`/trading/audit-log?limit=${limit}`);
  },

  getUpstoxLoginUrl(): Promise<{ login_url: string }> {
    return fetchApi("/auth/upstox/login-url");
  },

  getUpstoxAuthStatus(): Promise<{ authenticated: boolean; profile: unknown; connection_status: string }> {
    return fetchApi("/auth/upstox/status");
  },
};

export const systemApi = {
  getLiveDataHealth(): Promise<Record<string, "up" | "down">> {
    return fetchApi<Record<string, "up" | "down">>("/health/live-data");
  },
};

export const paperTradingApi = {
  submitOrder(order: {
    symbol: string;
    side: "BUY" | "SELL";
    quantity: number;
    order_type: "MARKET" | "LIMIT";
    limit_price?: number;
    signal_relation?: "AGREEMENT" | "AGAINST" | "INDEPENDENT" | "AUTO";
  }): Promise<unknown> {
    return fetchApi("/paper-trade/order", {
      method: "POST",
      body: JSON.stringify(order),
    });
  },
  getPositions(): Promise<unknown[]> {
    return fetchApi<unknown[]>("/paper-trade/positions");
  },
  getHistory(): Promise<unknown[]> {
    return fetchApi<unknown[]>("/paper-trade/history");
  },
  getPnl(): Promise<unknown> {
    return fetchApi<unknown>("/paper-trade/pnl");
  },
  resetWallet(): Promise<unknown> {
    return fetchApi<unknown>("/paper-trade/reset", { method: "POST" });
  },
  cancelOrder(orderId: string, symbol: string): Promise<unknown> {
    return fetchApi<unknown>(`/paper-trade/cancel/${encodeURIComponent(orderId)}?symbol=${encodeURIComponent(symbol)}`, { method: "POST" });
  },
};

export const signalsApi = {
  getSignal(symbol: string): Promise<SignalResponse> {
    return fetchApi(`/signals/${encodeURIComponent(symbol)}`);
  },
};

export const watchlistApi = {
  getWatchlist(list_id: number = 0): Promise<{ symbols: string[] }> {
    return fetchApi<{ symbols: string[] }>(`/watchlist?list_id=${list_id}`);
  },
  addSymbol(symbol: string, list_id: number = 0): Promise<{ symbols: string[] }> {
    return fetchApi<{ symbols: string[] }>("/watchlist", {
      method: "POST",
      body: JSON.stringify({ symbol, list_id }),
    });
  },
  removeSymbol(symbol: string, list_id: number = 0): Promise<{ symbols: string[] }> {
    return fetchApi<{ symbols: string[] }>(`/watchlist/${encodeURIComponent(symbol)}?list_id=${list_id}`, {
      method: "DELETE",
    });
  },
};

export const onboardingApi = {
  completeOnboarding(data: { profile: any; organization: any; marketPrefs: any; workspace: any }): Promise<any> {
    return fetchApi("/onboarding", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }
};
