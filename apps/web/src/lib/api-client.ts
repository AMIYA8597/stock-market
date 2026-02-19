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

export const marketApi = {
  getQuote(symbol: string): Promise<Quote> {
    return fetchApi(`/market/quote/${encodeURIComponent(symbol)}`);
  },

  getHistory(
    symbol: string,
    interval: string = "1D",
    start?: string,
    end?: string
  ): Promise<HistoryResponse> {
    const params = new URLSearchParams({ interval });
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    return fetchApi(
      `/market/history/${encodeURIComponent(symbol)}?${params.toString()}`
    );
  },

  getQuotes(symbols: string[]): Promise<Quote[]> {
    return fetchApi("/market/quotes", {
      method: "POST",
      body: JSON.stringify({ symbols }),
    });
  },
};

// ─── Screener ───────────────────────────────────────

export const screenerApi = {
  search(filters: Partial<ScreenerFilter>): Promise<ScreenerResponse> {
    return fetchApi("/screener/search", {
      method: "POST",
      body: JSON.stringify(filters),
    });
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
    return fetchApi("/alerts");
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
    return fetchApi(`/alerts/history${params}`);
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
