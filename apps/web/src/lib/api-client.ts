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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_PREFIX = "/api/v1";

type UnknownRecord = Record<string, unknown>;

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

async function fetchApi<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${API_PREFIX}${path}`;
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("nq_access_token")
      : null;

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
  }): Promise<TokenResponse> {
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
};

// ─── Market Data ────────────────────────────────────

const normalizeInterval = (interval: string): string => {
  const map: Record<string, string> = {
    "1D": "1d",
    "1H": "1h",
    "15M": "15m",
    "5M": "5m",
    "1M": "1m",
  };
  const upper = interval.toUpperCase();
  return map[upper] ?? interval;
};

const mapQuote = (raw: UnknownRecord): Quote => {
  const price = typeof raw.price === "number" ? raw.price : 0;
  const change = typeof raw.change === "number" ? raw.change : 0;
  const changePct =
    typeof raw.change_percent === "number"
      ? raw.change_percent
      : typeof raw.change_pct === "number"
        ? raw.change_pct
        : 0;
  const symbol = typeof raw.symbol === "string" ? raw.symbol : typeof raw.ticker === "string" ? raw.ticker : "UNKNOWN";

  return {
    symbol,
    price,
    change,
    change_percent: changePct,
    volume: typeof raw.volume === "number" ? raw.volume : 0,
    high: typeof raw.high === "number" ? raw.high : typeof raw.high_52w === "number" ? raw.high_52w : price,
    low: typeof raw.low === "number" ? raw.low : typeof raw.low_52w === "number" ? raw.low_52w : price,
    open: typeof raw.open === "number" ? raw.open : price - change,
    previous_close: typeof raw.previous_close === "number" ? raw.previous_close : price - change,
    timestamp: typeof raw.timestamp === "string" ? raw.timestamp : new Date().toISOString(),
  };
};

const mapHistory = (raw: UnknownRecord): HistoryResponse => {
  const rawBars = Array.isArray(raw.bars)
    ? (raw.bars as UnknownRecord[])
    : Array.isArray(raw.data)
      ? (raw.data as UnknownRecord[])
      : [];

  const bars = rawBars.map((bar) => ({
    timestamp:
      typeof bar.timestamp === "string"
        ? bar.timestamp
        : typeof bar.time === "string"
          ? bar.time
          : new Date().toISOString(),
    open: typeof bar.open === "number" ? bar.open : 0,
    high: typeof bar.high === "number" ? bar.high : 0,
    low: typeof bar.low === "number" ? bar.low : 0,
    close: typeof bar.close === "number" ? bar.close : 0,
    volume: typeof bar.volume === "number" ? bar.volume : 0,
    adjusted_close:
      typeof bar.adjusted_close === "number"
        ? bar.adjusted_close
        : undefined,
  }));

  return {
    symbol: typeof raw.symbol === "string" ? raw.symbol : "UNKNOWN",
    interval: typeof raw.interval === "string" ? raw.interval : "1d",
    bars,
    count: typeof raw.count === "number" ? raw.count : bars.length,
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
    end?: string
  ): Promise<HistoryResponse> {
    const normalizedInterval = normalizeInterval(interval);
    const params = new URLSearchParams({ interval: normalizedInterval });
    if (start) params.set("start", start);
    if (end) params.set("end", end);
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
    const payload = {
      exchange: [filters.exchange ?? "NSE"],
      filters,
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

        const price = typeof item.price === "number" ? item.price : 0;

        return {
          symbol,
          name: typeof item.name === "string" ? item.name : symbol,
          asset_class: "equity",
          exchange: "NSE",
          sector: null,
          price,
          change_percent: typeof item.sharpe_21d === "number" ? item.sharpe_21d : 0,
          volume: 0,
          market_cap: null,
          rsi: typeof item.rsi === "number" ? item.rsi : null,
          ml_signal: typeof item.signal === "string" ? item.signal : null,
          ml_confidence: null,
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

export { ApiError };
