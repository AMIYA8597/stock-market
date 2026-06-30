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
} from "@neuroquant/types";
import { getApiBaseUrl } from "@/lib/runtime-config";

const API_BASE = getApiBaseUrl();
const API_PREFIX = "/api/v1";
const ACCESS_TOKEN_KEY = "nq_access_token";
const REFRESH_TOKEN_KEY = "nq_refresh_token";

type UnknownRecord = Record<string, unknown>;

function parseNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : fallback;
  }
  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }
  return fallback;
}


class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body: unknown
  ) {
    super(`API Error ${status}: ${statusText}`);
    this.name = "ApiError";
  }
}

let refreshPromise: Promise<string | null> | null = null;

function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setAuthTokens(tokens: { access_token: string; refresh_token: string }): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function clearAuthTokens(): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    clearAuthTokens();
    return null;
  }

  if (!refreshPromise) {
    refreshPromise = (async () => {
      const url = `${API_BASE}${API_PREFIX}/auth/refresh`;
      const response = await fetch(url, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        clearAuthTokens();
        return null;
      }

      const data = (await response.json()) as TokenResponse;
      setAuthTokens({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
      });
      return data.access_token;
    })().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

async function fetchApi<T>(
  path: string,
  options: RequestInit = {},
  retryCount = 0
): Promise<T> {
  const url = `${API_BASE}${API_PREFIX}${path}`;
  const token = getAccessToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    if (response.status === 401 && retryCount < 1) {
      const nextToken = await refreshAccessToken();
      if (nextToken) {
        return fetchApi<T>(path, options, retryCount + 1);
      }
    }

    if (response.status >= 500 && retryCount < 2) {
      await new Promise((resolve) => setTimeout(resolve, 250 * (retryCount + 1)));
      return fetchApi<T>(path, options, retryCount + 1);
    }

    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, response.statusText, body);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

// ─── Auth ────────────────────────────────────────────

export const authApi = {
  register(data: {
    email: string;
    password: string;
    full_name: string;
  }): Promise<{ id: string; email: string; full_name: string; created_at: string }> {
    return fetchApi("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  login(email: string, password: string): Promise<TokenResponse> {
    return fetchApi("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  refreshToken(refresh_token: string): Promise<TokenResponse> {
    return fetchApi("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    });
  },

  getProfile(): Promise<UserProfile> {
    return fetchApi("/auth/me");
  },

  logout(): Promise<void> {
    return fetchApi("/auth/logout", { method: "POST" });
  },

  forgotPassword(email: string): Promise<{ message: string }> {
    return fetchApi("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },

  resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
    return fetchApi("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
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
  methods(): Promise<{ methods: Array<{ code: string; min_amount: string; max_amount: string; enabled: boolean }> }> {
    return fetchApi("/payments/methods");
  },
  balance(): Promise<{ currency: string; wallet_balance: string }> {
    return fetchApi("/payments/balance");
  },
  async createIntent(data: { amount: number; method: "UPI" | "CARD" | "NETBANKING"; currency?: string; description?: string }): Promise<{ intent_id: string; provider_ref: string; amount: string; status: string }> {
    const idem = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `idem-${Date.now()}`;
    return fetchApi("/payments/intents", {
      method: "POST",
      headers: { "Idempotency-Key": idem },
      body: JSON.stringify(data),
    });
  },
  confirmIntent(intent_id: string, confirmation_code: string): Promise<{ intent_id: string; status: string; credited_amount: string; completed_at: string | null }> {
    return fetchApi("/payments/confirm", {
      method: "POST",
      body: JSON.stringify({ intent_id, confirmation_code }),
    });
  },
  history(limit = 20): Promise<{ items: Array<{ intent_id: string; amount: string; currency: string; method: string; status: string; created_at: string }>; total: number }> {
    return fetchApi(`/payments/history?limit=${limit}`);
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

const mapQuote = (raw: UnknownRecord): Quote => {
  const price = parseNumber(raw.price);
  const change = parseNumber(raw.change);
  const changePct = parseNumber(
    raw.change_percent !== undefined ? raw.change_percent : raw.change_pct
  );
  const symbol = typeof raw.symbol === "string" ? raw.symbol : typeof raw.ticker === "string" ? raw.ticker : "UNKNOWN";

  return {
    symbol,
    price,
    change,
    change_percent: changePct,
    volume: parseNumber(raw.volume),
    high: parseNumber(raw.high !== undefined ? raw.high : raw.high_52w, price),
    low: parseNumber(raw.low !== undefined ? raw.low : raw.low_52w, price),
    open: parseNumber(raw.open, price - change),
    previous_close: parseNumber(raw.previous_close, price - change),
    timestamp: typeof raw.timestamp === "string" ? raw.timestamp : new Date().toISOString(),
  };
};

const mapHistory = (raw: UnknownRecord): HistoryResponse => {
  const rawBars = Array.isArray(raw.bars)
    ? (raw.bars as UnknownRecord[])
    : Array.isArray(raw.data)
      ? (raw.data as UnknownRecord[])
      : [];

  const bars = rawBars.map((bar) => {
    let timestamp = new Date().toISOString();
    if (typeof bar.timestamp === "string") {
      timestamp = bar.timestamp;
    } else if (typeof bar.time === "string") {
      timestamp = bar.time;
    } else if (typeof bar.time === "number") {
      timestamp = new Date(bar.time * 1000).toISOString();
    } else if (typeof bar.timestamp === "number") {
      timestamp = new Date(bar.timestamp * 1000).toISOString();
    }

    return {
      timestamp,
      open: parseNumber(bar.open),
      high: parseNumber(bar.high),
      low: parseNumber(bar.low),
      close: parseNumber(bar.close),
      volume: parseNumber(bar.volume),
      adjusted_close:
        bar.adjusted_close !== undefined && bar.adjusted_close !== null
          ? parseNumber(bar.adjusted_close)
          : undefined,
    };
  });

  return {
    symbol: typeof raw.symbol === "string" ? raw.symbol : "UNKNOWN",
    interval: typeof raw.interval === "string" ? raw.interval : "1d",
    bars,
    count: parseNumber(raw.count, bars.length),
  };
};

export const marketApi = {
  getQuote(symbol: string): Promise<Quote> {
    return fetchApi<UnknownRecord>(`/market/quote/${encodeURIComponent(symbol)}`).then(
      mapQuote
    );
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
    const settled = await Promise.allSettled(
      symbols.map((symbol) => marketApi.getQuote(symbol))
    );
    return settled
      .filter((result): result is PromiseFulfilledResult<Quote> => result.status === "fulfilled")
      .map((result) => result.value);
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

        const price = parseNumber(item.price);
        const changePercent = parseNumber(item.change_pct ?? item.change_percent ?? item.sharpe_21d);
        const volume = parseNumber(item.volume ?? item.volume_ratio);
        const marketCap = item.market_cap !== undefined && item.market_cap !== null ? parseNumber(item.market_cap) : null;
        const rsi = item.rsi !== undefined && item.rsi !== null ? parseNumber(item.rsi) : null;
        const mlSignal = typeof item.signal_direction === "string" ? item.signal_direction : typeof item.signal === "string" ? item.signal : null;
        const mlConfidence = item.signal_confidence !== undefined && item.signal_confidence !== null ? parseNumber(item.signal_confidence) : item.ml_confidence !== undefined && item.ml_confidence !== null ? parseNumber(item.ml_confidence) : null;

        return {
          symbol,
          name: typeof item.name === "string" ? item.name : symbol,
          asset_class: typeof item.asset_type === "string" ? item.asset_type : "equity",
          exchange: typeof item.exchange === "string" ? item.exchange : "NSE",
          sector: typeof item.sector === "string" ? item.sector : null,
          price,
          change_percent: changePercent,
          volume,
          market_cap: marketCap,
          rsi,
          ml_signal: mlSignal,
          ml_confidence: mlConfidence,
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
    return fetchApi(`/portfolio/${portfolioId}/risk`);
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
    return fetchApi<UnknownRecord[]>("/alerts").then((rawItems) =>
      rawItems.map((raw, index) => {
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
    return fetchApi("/alerts", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update(
    id: string,
    data: Partial<AlertDefinition>
  ): Promise<AlertDefinition> {
    return fetchApi(`/alerts/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
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
    return fetchApi(`/predictions/research/${encodeURIComponent(symbol)}`, {
      method: "POST",
    });
  },

  getRegime(symbol: string): Promise<RegimeData> {
    return fetchApi(`/predictions/regime/${encodeURIComponent(symbol)}`);
  },

  getCorrelationGraph(): Promise<{
    nodes: CorrelationNode[];
    edges: CorrelationEdge[];
  }> {
    return fetchApi("/predictions/correlation-graph");
  },
};

export const tradingApi = {
  getMode(): Promise<{ trading_mode: string; connection_status: string; authenticated: boolean; profile: unknown }> {
    return fetchApi("/trading/mode");
  },

  setMode(mode: string): Promise<{ status: string; trading_mode: string; message: string }> {
    return fetchApi("/trading/mode", {
      method: "POST",
      body: JSON.stringify({ mode }),
    });
  },

  placeOrder(order: {
    symbol: string;
    side: string;
    quantity: number;
    order_type: string;
    limit_price?: number;
    product?: string;
  }): Promise<unknown> {
    return fetchApi("/trading/order", {
      method: "POST",
      body: JSON.stringify(order),
    });
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

export { ApiError };
