import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi, setAuthTokens, clearAuthTokens } from "@/lib/api-client";
import { ApiError } from "@/lib/api-client";
import type { UserProfile } from "@neuroquant/types";

interface AuthState {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setUser: (user: UserProfile | null) => void;
  setTokens: (tokens: { access_token: string; refresh_token: string }) => Promise<void>;
  logout: () => Promise<void>;
  fetchProfile: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true, // start loading initially to allow profile fetch on hydration
      error: null,

      setUser: (user) => set({ user, isAuthenticated: !!user, isLoading: false }),

      setTokens: async (tokens) => {
        setAuthTokens(tokens);
        set({ isAuthenticated: true, isLoading: true, error: null });
        await get().fetchProfile();
      },

      logout: async () => {
        try {
          // Attempt server logout, but always clear local state regardless
          await authApi.logout();
        } catch (e) {
          console.error("Server logout failed", e);
        } finally {
          clearAuthTokens();
          set({ user: null, isAuthenticated: false, error: null, isLoading: false });
        }
      },

      fetchProfile: async () => {
        if (typeof window !== "undefined" && !localStorage.getItem("nq_access_token")) {
          set({ isAuthenticated: false, isLoading: false, user: null });
          return;
        }

        set({ isLoading: true, error: null });
        try {
          const profile = await authApi.getProfile();
          set({ user: profile, isAuthenticated: true, isLoading: false });
        } catch (err: unknown) {
          console.error("fetchProfile failed:", err);
          if (err instanceof ApiError && err.status === 401) {
            clearAuthTokens();
            set({ user: null, isAuthenticated: false, isLoading: false, error: "Session expired. Please log in again." });
          } else {
            set({ isLoading: false, error: "Unable to load profile. Please try again later." });
          }
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({ isAuthenticated: state.isAuthenticated }), // Only persist auth boolean for instant UI, but always re-fetch user
    }
  )
);
