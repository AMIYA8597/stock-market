// @vitest-environment node
import { describe, test, expect } from 'vitest';
import { getLocalSession, parseJwtExp } from '../lib/auth-session';

describe('auth-session tests', () => {
  test('parseJwtExp correctly extracts exp timestamp from valid JWT', () => {
    const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
    const payload = Buffer.from(JSON.stringify({ sub: 'user_123', exp: 1790383317 })).toString('base64url');
    const token = `${header}.${payload}.mockSignature`;

    const exp = parseJwtExp(token);
    expect(exp).toBe(1790383317);
  });

  test('parseJwtExp returns null for invalid tokens', () => {
    expect(parseJwtExp('')).toBeNull();
    expect(parseJwtExp('not-a-jwt')).toBeNull();
    expect(parseJwtExp('a.not_json.sig')).toBeNull();
  });

  test('getLocalSession returns null when no cookies are present', () => {
    const mockRequest = {
      cookies: {
        getAll: () => [],
        get: () => undefined,
      },
    };
    expect(getLocalSession(mockRequest as any)).toBeNull();
  });

  test('getLocalSession extracts valid unexpired session from single cookie', () => {
    const testToken = ['sample', Buffer.from(JSON.stringify({ exp: 1999999999 })).toString('base64url'), 'signature'].join('.');
    const sessionData = {
      access_token: testToken,
      refresh_token: 'mock_refresh',
      expires_at: 1999999999,
      user: { id: 'usr_1' },
    };
    const b64Val = 'base64-' + Buffer.from(JSON.stringify(sessionData)).toString('base64url');

    const mockRequest = {
      cookies: {
        getAll: () => [{ name: 'sb-avizvhsyqyrtyszgfjiv-auth-token', value: b64Val }],
        get: (name: string) =>
          name === 'sb-avizvhsyqyrtyszgfjiv-auth-token' ? { name, value: b64Val } : undefined,
      },
    };

    const session = getLocalSession(mockRequest as any);
    expect(session).not.toBeNull();
    expect(session?.access_token).toBe(sessionData.access_token);
    expect(session?.expires_at).toBe(1999999999);
  });

  test('getLocalSession reassembles chunked cookies properly', () => {
    const chunkToken = ['chunk', Buffer.from(JSON.stringify({ exp: 1999999999 })).toString('base64url'), 'signature'].join('.');
    const sessionData = {
      access_token: chunkToken,
      refresh_token: 'chunked_refresh',
      expires_at: 1999999999,
    };
    const b64Val = 'base64-' + Buffer.from(JSON.stringify(sessionData)).toString('base64url');
    const chunk0 = b64Val.slice(0, 25);
    const chunk1 = b64Val.slice(25);

    const mockRequest = {
      cookies: {
        getAll: () => [
          { name: 'sb-myproj-auth-token.0', value: chunk0 },
          { name: 'sb-myproj-auth-token.1', value: chunk1 },
        ],
        get: (name: string) => {
          if (name === 'sb-myproj-auth-token.0') return { name, value: chunk0 };
          if (name === 'sb-myproj-auth-token.1') return { name, value: chunk1 };
          return undefined;
        },
      },
    };

    const session = getLocalSession(mockRequest as any);
    expect(session).not.toBeNull();
    expect(session?.access_token).toBe(sessionData.access_token);
    expect(session?.refresh_token).toBe('chunked_refresh');
  });
});
