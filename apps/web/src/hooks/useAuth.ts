"use client";

import { useEffect, useRef } from "react";
import { useAuthStore } from "@/stores/authStore";

export function useAuth() {
  const { user, isAuthenticated, isLoading, error, fetchProfile, logout } = useAuthStore();
  const fetched = useRef(false);

  useEffect(() => {
    // Only attempt fetch once on mount to avoid infinite loops if it fails
    if (!fetched.current) {
      fetched.current = true;
      void fetchProfile();
    }
  }, [fetchProfile]);

  return { user, isAuthenticated, isLoading, error, logout };
}
