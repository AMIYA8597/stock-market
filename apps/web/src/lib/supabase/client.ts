import { createBrowserClient } from '@supabase/ssr';
// import { getApiBaseUrl } from '../runtime-config';

export function createClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const supabaseKey = (process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY)!;

  return createBrowserClient(
    supabaseUrl,
    supabaseKey
  );
}
