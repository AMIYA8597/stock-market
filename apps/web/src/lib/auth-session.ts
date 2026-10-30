import type { NextRequest } from 'next/server';

export interface LocalSession {
  access_token: string;
  refresh_token?: string;
  expires_at?: number;
  user?: unknown;
}

export function parseJwtExp(token: string): number | null {
  try {
    const parts = token.split('.');
    const part = parts[1];
    if (parts.length < 2 || !part) return null;
    const base64 = part.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
    const jsonPayload = atob(padded);
    const decoded = JSON.parse(jsonPayload);
    return typeof decoded.exp === 'number' ? decoded.exp : null;
  } catch {
    return null;
  }
}

export function getLocalSession(request: Pick<NextRequest, 'cookies'>): LocalSession | null {
  const allCookies = request.cookies.getAll();
  const authCookie = allCookies.find(
    (c) => c.name.startsWith('sb-') && c.name.includes('-auth-token')
  );
  if (!authCookie) return null;

  const baseKey = authCookie.name.replace(/\.\d+$/, '');
  let fullValue = '';
  const singleCookie = request.cookies.get(baseKey);
  if (singleCookie?.value) {
    fullValue = singleCookie.value;
  } else {
    const chunks: string[] = [];
    for (let i = 0; ; i++) {
      const chunk = request.cookies.get(`${baseKey}.${i}`);
      if (!chunk?.value) break;
      chunks.push(chunk.value);
    }
    fullValue = chunks.join('');
  }

  if (!fullValue) return null;

  let raw = fullValue;
  if (raw.startsWith('base64-')) {
    try {
      const b64 = raw.slice(7).replace(/-/g, '+').replace(/_/g, '/');
      const padded = b64.padEnd(b64.length + ((4 - (b64.length % 4)) % 4), '=');
      raw = atob(padded);
    } catch {
      return null;
    }
  }

  try {
    const data = JSON.parse(raw);
    if (!data) return null;
    if (Array.isArray(data)) {
      return {
        access_token: data[0],
        refresh_token: data[1],
        expires_at: parseJwtExp(data[0]) ?? undefined,
      };
    }
    const session = data as LocalSession;
    if (session.access_token && !session.expires_at) {
      session.expires_at = parseJwtExp(session.access_token) ?? undefined;
    }
    return session;
  } catch {
    return null;
  }
}
