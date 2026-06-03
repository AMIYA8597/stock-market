import type { SignalResponse, ForecastResponse } from "@/types/intelligence";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

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
    return parseJson<SignalResponse>(response);
  },

  async getBulkSignals(symbols: string[]): Promise<SignalResponse[]> {
    const params = new URLSearchParams({ symbols: symbols.join(",") });
    const response = await fetch(`${API_URL}/signals/bulk?${params.toString()}`, {
      method: "GET",
      cache: "no-store",
    });
    return parseJson<{ signals: SignalResponse[] }>(response).then((data) => data.signals);
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
