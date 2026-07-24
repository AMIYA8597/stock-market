import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi, setAuthTokens, clearAuthTokens } from "@/lib/api-client";
import type { UserProfile } from "@neuroquant/types";

interface AuthState {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setUser: (user: UserProfile | null) => void;
  setTokens: (tokens: { access_token: string; refresh_token: string }) => void;
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

      setTokens: (tokens) => {
        setAuthTokens(tokens);
        set({ isAuthenticated: true });
        // After setting tokens, fetch the user profile
        get().fetchProfile();
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
        // If we know there are no tokens in localStorage, skip fetching
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
          // If the profile fetch fails, it might be due to an expired refresh token
          clearAuthTokens();
          set({ user: null, isAuthenticated: false, isLoading: false, error: "Session expired. Please log in again." });
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({ isAuthenticated: state.isAuthenticated }), // Only persist auth boolean for instant UI, but always re-fetch user
    }
  )
);
