const API_V1_SEGMENT = "/api/v1";

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function stripApiV1Suffix(value: string): string {
  return value.replace(/\/api\/v1\/?$/i, "");
}

function normalizeHttpBaseUrl(value: string | undefined, fallback: string): string {
  const candidate = trimTrailingSlash(value?.trim() || fallback);
  return stripApiV1Suffix(candidate);
}

export function getApiBaseUrl(): string {
  return normalizeHttpBaseUrl(process.env.NEXT_PUBLIC_API_URL, "http://localhost:8000");
}

export function getApiV1Url(): string {
  return `${getApiBaseUrl()}${API_V1_SEGMENT}`;
}

export function getWsBaseUrl(): string {
  const explicitWsUrl = process.env.NEXT_PUBLIC_WS_URL?.trim();
  if (explicitWsUrl) {
    return trimTrailingSlash(explicitWsUrl).replace(/\/ws\/?$/i, "");
  }

  const apiBase = getApiBaseUrl();
  if (apiBase.startsWith("https://")) {
    return `wss://${apiBase.slice("https://".length)}`;
  }
  if (apiBase.startsWith("http://")) {
    return `ws://${apiBase.slice("http://".length)}`;
  }
  return apiBase;
}

