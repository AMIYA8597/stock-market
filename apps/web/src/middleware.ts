import { NextResponse, type NextRequest } from 'next/server';
import { createServerClient, type CookieOptions } from '@supabase/ssr';
import type { Session } from '@supabase/supabase-js';
import createMiddleware from 'next-intl/middleware';
import { routing } from './i18n/routing';

const intlMiddleware = createMiddleware(routing);

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
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

export async function middleware(request: NextRequest) {
  // First, run next-intl middleware to handle locales
  const response = intlMiddleware(request);

  let session: Session | null = null;

  if (isSupabaseConfigured) {
    // Then, attach supabase to the response to refresh sessions
    const supabase = createServerClient(supabaseUrl!, supabaseAnonKey!, {
      cookies: {
        get(name: string) {
          return request.cookies.get(name)?.value;
        },
        set(name: string, value: string, options: CookieOptions) {
          request.cookies.set({
            name,
            value,
            ...options,
          });
          response.cookies.set({
            name,
            value,
            ...options,
          });
        },
        remove(name: string, options: CookieOptions) {
          request.cookies.set({
            name,
            value: '',
            ...options,
          });
          response.cookies.set({
            name,
            value: '',
            ...options,
          });
        },
      },
    });

    ({ data: { session } } = await supabase.auth.getSession());
  } else if (!warnedMissingSupabaseConfig) {
    warnedMissingSupabaseConfig = true;
    console.warn(
      '[middleware] NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY are not set. ' +
        'Auth is disabled: every request is treated as unauthenticated and protected routes will redirect to /login.'
    );
  }

  // Handle protected routes
  const pathname = request.nextUrl.pathname;
  const hasLocale = pathname.match(/^\/(en|hi|bn)(\/|$)/);
  const pathWithoutLocale = hasLocale ? pathname.replace(/^\/(en|hi|bn)/, '') || '/' : pathname;
  
  const isPublicPath = ['/', '/login', '/register', '/forgot-password', '/reset-password', '/pricing', '/blog'].includes(pathWithoutLocale) || pathWithoutLocale.startsWith('/blog/');

  // Remembers where an unauthenticated visitor was headed so login can send
  // them back there - kept in a cookie rather than a ?next= query param so
  // it never shows up in the address bar.
  const NEXT_COOKIE = 'nq_next';

  if (!session && !isPublicPath && !pathname.startsWith('/api') && !pathname.startsWith('/_next') && !pathname.match(/\.(.*)$/)) {
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

  if (session && ['/login', '/register', '/forgot-password'].includes(pathWithoutLocale)) {
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
