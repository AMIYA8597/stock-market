# DEPLOYMENT_VERCEL.md

## Overview
This document outlines the deployment process for the `@neuroquant/web` frontend on Vercel.

## Vercel Project Configuration

1. **Root Directory**: Select `apps/web` as the root directory for the Vercel project, OR set the root to `/` and set the build command to `npx turbo build --filter=@neuroquant/web...`
2. **Framework Preset**: Next.js
3. **Build Command**: `pnpm run build`
4. **Install Command**: `pnpm install`

## Environment Variables

Configure the following variables in the Vercel project settings:

```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci...
```

**SECURITY WARNING**: Never commit `NEXT_PUBLIC_SUPABASE_ANON_KEY` or expose service role keys to the browser.

## Monorepo Considerations
- `turbo.json` handles build caching. Vercel automatically caches `.next` and `node_modules`.
- Shared packages (`@neuroquant/ui`, `@neuroquant/config`) are transpiled.

## Post-Deployment Validation
1. Verify Auth Guard redirects to `/login` when unauthenticated.
2. Verify onboarding flow saves preferences.
3. Validate API interactions bypass CORS by using rewrites correctly if backend is on a separate domain.
