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

function isLocalHostname(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1";
}

function shouldUseRelativeApiProxy(baseUrl: string): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  try {
    const current = new URL(window.location.origin);
    // On production/Vercel (non-localhost), always use relative URLs so that
    // Next.js server-side rewrites proxy the request to the backend.
    // This avoids CORS entirely — the browser only ever sees the same origin.
    if (!isLocalHostname(current.hostname)) {
      return true;
    }
    const target = new URL(baseUrl);
    return isLocalHostname(target.hostname);
  } catch {
    return false;
  }
}

export function getApiBaseUrl(): string {
  const baseUrl = normalizeHttpBaseUrl(process.env.NEXT_PUBLIC_API_URL, "http://localhost:8000");
  return shouldUseRelativeApiProxy(baseUrl) ? "" : baseUrl;
}

export function getApiV1Url(): string {
  return `${getApiBaseUrl()}${API_V1_SEGMENT}`;
}

export function getWsBaseUrl(): string {
  const explicitWsUrl = process.env.NEXT_PUBLIC_WS_URL?.trim();
  if (explicitWsUrl) {
    return trimTrailingSlash(explicitWsUrl).replace(/\/ws\/?$/i, "");
  }

  // Raw API base before relative proxy substitution
  const rawApiBase = normalizeHttpBaseUrl(
    process.env.NEXT_PUBLIC_API_URL,
    typeof window !== "undefined" && !isLocalHostname(window.location.hostname)
      ? "https://neuroquant-api-6g57r5groa-el.a.run.app"
      : "http://localhost:8000"
  );

  if (rawApiBase.startsWith("https://")) {
    return `wss://${rawApiBase.slice("https://".length)}`;
  }
  if (rawApiBase.startsWith("http://")) {
    return `ws://${rawApiBase.slice("http://".length)}`;
  }

  if (typeof window !== "undefined") {
    if (!isLocalHostname(window.location.hostname)) {
      return "wss://neuroquant-api-6g57r5groa-el.a.run.app";
    }
    return "ws://localhost:8000";
  }

  return rawApiBase;
}
