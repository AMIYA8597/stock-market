"use client";

import { useEffect, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

interface AuthGuardProps {
  children: ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps): JSX.Element {
  const { isAuthenticated, isLoading, user, error } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace(`/login?callbackUrl=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, isAuthenticated, router, pathname, error, user]);

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[var(--bg-base)]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-t-2 border-[var(--border-subtle)] border-t-[var(--accent-cyan)]"></div>
          <p className="text-sm font-medium tracking-wider text-[var(--text-secondary)] uppercase">
            Loading session...
          </p>
        </div>
      </div>
    );
  }

  // If not authenticated, we're redirecting, render nothing to avoid flash of content
  if (!isAuthenticated) {
    return <></>;
  }

  return <>{children}</>;
}
