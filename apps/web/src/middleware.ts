import { NextResponse, type NextRequest } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import type { Session } from '@supabase/supabase-js';
import createMiddleware from 'next-intl/middleware';
import { routing } from './i18n/routing';

const intlMiddleware = createMiddleware(routing);

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

// Both @supabase/ssr's createServerClient() and the browser client throw
// immediately if these are missing/empty, which previously crashed every
// single request (including public marketing pages) with a 500 the moment
// NEXT_PUBLIC_SUPABASE_URL/ANON_KEY weren't configured. Real auth genuinely
// requires real credentials, but a misconfigured/unset Supabase project
// must not take down the entire app - it must just mean no one can have a
// session, which the existing "no session -> redirect to /login" logic
// below already handles correctly.
const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);
let warnedMissingSupabaseConfig = false;

import { getLocalSession } from './lib/auth-session';

export async function middleware(request: NextRequest) {
  // First, run next-intl middleware to handle locales
  const response = intlMiddleware(request);

  const pathname = request.nextUrl.pathname;
  const hasLocale = pathname.match(/^\/(en|hi|bn)(\/|$)/);
  const pathWithoutLocale = hasLocale ? pathname.replace(/^\/(en|hi|bn)/, '') || '/' : pathname;

  if (pathname.startsWith('/api') || pathname.startsWith('/_next') || pathname.match(/\.(.*)$/)) {
    return response;
  }

  // Purely public marketing paths return immediately without any auth overhead
  const isMarketingPath = ['/', '/pricing', '/blog'].includes(pathWithoutLocale) || pathWithoutLocale.startsWith('/blog/');
  if (isMarketingPath) {
    return response;
  }

  const isAuthEntryPath = ['/login', '/register', '/forgot-password', '/reset-password'].includes(pathWithoutLocale);
  const NEXT_COOKIE = 'nq_next';

  if (!isSupabaseConfigured) {
    if (!warnedMissingSupabaseConfig) {
      warnedMissingSupabaseConfig = true;
      console.warn(
        '[middleware] NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY are not set. ' +
          'Auth is disabled: every request is treated as unauthenticated and protected routes will redirect to /login.'
      );
    }
    if (!isAuthEntryPath) {
      const url = request.nextUrl.clone();
      url.pathname = `/${hasLocale ? pathname.split('/')[1] : 'en'}/login`;
      url.search = '';
      const redirect = NextResponse.redirect(url);
      redirect.cookies.set(NEXT_COOKIE, pathWithoutLocale, {
        maxAge: 600,
        path: '/',
        httpOnly: true,
        sameSite: 'lax',
      });
      return redirect;
    }
    return response;
  }

  // Inspect local session in cookies
  const localSession = getLocalSession(request);
  const nowInSeconds = Math.floor(Date.now() / 1000);

  let hasValidSession = false;
  let hasExpiredSession = false;

  if (localSession?.access_token) {
    if (localSession.expires_at && localSession.expires_at > nowInSeconds + 30) {
      hasValidSession = true;
    } else {
      hasExpiredSession = true;
    }
  }

  // If session is expired or expiring, attempt refresh with strict 1000ms timeout
  if (hasExpiredSession && localSession?.refresh_token) {
    try {
      const supabase = createServerClient(supabaseUrl!, supabaseAnonKey!, {
        cookies: {
          getAll() {
            return request.cookies.getAll();
          },
          setAll(cookiesToSet) {
            cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
            cookiesToSet.forEach(({ name, value, options }) =>
              response.cookies.set(name, value, options)
            );
          },
        },
      });

      const timeoutPromise = new Promise<{ data: { session: Session | null }; error: Error }>((resolve) =>
        setTimeout(() => resolve({ data: { session: null }, error: new Error('Auth refresh timeout') }), 1000)
      );

      const result = await Promise.race([supabase.auth.getSession(), timeoutPromise]);
      if (result.data?.session) {
        hasValidSession = true;
      }
    } catch (err) {
      console.warn('[middleware] Supabase session refresh failed or timed out:', err);
    }
  }

  // Handle protected routes
  if (!hasValidSession && !isAuthEntryPath) {
    const url = request.nextUrl.clone();
    url.pathname = `/${hasLocale ? pathname.split('/')[1] : 'en'}/login`;
    url.search = '';
    const redirect = NextResponse.redirect(url);
    redirect.cookies.set(NEXT_COOKIE, pathWithoutLocale, {
      maxAge: 600,
      path: '/',
      httpOnly: true,
      sameSite: 'lax',
    });
    if (hasExpiredSession) {
      const allCookies = request.cookies.getAll();
      allCookies
        .filter((c) => c.name.startsWith('sb-') && c.name.includes('-auth-token'))
        .forEach((c) => {
          redirect.cookies.delete(c.name);
        });
    }
    return redirect;
  }

  if (hasValidSession && ['/login', '/register', '/forgot-password'].includes(pathWithoutLocale)) {
    const locale = hasLocale ? pathname.split('/')[1] : 'en';
    const storedNext = request.cookies.get(NEXT_COOKIE)?.value;
    const destination = storedNext && storedNext.startsWith('/') ? storedNext : '/dashboard';
    const url = request.nextUrl.clone();
    url.pathname = `/${locale}${destination}`;
    url.search = '';
    const redirect = NextResponse.redirect(url);
    redirect.cookies.delete(NEXT_COOKIE);
    return redirect;
  }

  return response;
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};

