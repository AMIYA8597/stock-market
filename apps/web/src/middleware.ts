import { NextResponse, type NextRequest } from 'next/server';
import { createServerClient, type CookieOptions } from '@supabase/ssr';
import createMiddleware from 'next-intl/middleware';
import { routing } from './i18n/routing';

const intlMiddleware = createMiddleware(routing);

export async function middleware(request: NextRequest) {
  // First, run next-intl middleware to handle locales
  const response = intlMiddleware(request);

  // Then, attach supabase to the response to refresh sessions
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
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
    }
  );

  const { data: { session } } = await supabase.auth.getSession();

  // Handle protected routes
  const pathname = request.nextUrl.pathname;
  const hasLocale = pathname.match(/^\/(en|hi|bn)(\/|$)/);
  const pathWithoutLocale = hasLocale ? pathname.replace(/^\/(en|hi|bn)/, '') || '/' : pathname;
  
  const isPublicPath = ['/', '/login', '/register', '/forgot-password', '/reset-password', '/pricing', '/blog'].includes(pathWithoutLocale) || pathWithoutLocale.startsWith('/blog/');

  if (!session && !isPublicPath && !pathname.startsWith('/api') && !pathname.startsWith('/_next') && !pathname.match(/\.(.*)$/)) {
    const url = request.nextUrl.clone();
    url.pathname = `/${hasLocale ? pathname.split('/')[1] : 'en'}/login`;
    url.searchParams.set('next', pathname);
    return NextResponse.redirect(url);
  }

  if (session && ['/login', '/register', '/forgot-password'].includes(pathWithoutLocale)) {
    const url = request.nextUrl.clone();
    url.pathname = `/${hasLocale ? pathname.split('/')[1] : 'en'}/dashboard`;
    return NextResponse.redirect(url);
  }

  return response;
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};
