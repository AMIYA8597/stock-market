import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi, ApiError } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import type { UserProfile } from "@neuroquant/types";

interface AuthState {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setUser: (user: UserProfile | null) => void;
  logout: () => Promise<void>;
  fetchProfile: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      error: null,

      setUser: (user) => set({ user, isAuthenticated: !!user, isLoading: false }),

      logout: async () => {
        try {
          const supabase = createClient();
          await supabase.auth.signOut();
        } catch (e) {
          console.error("Supabase logout failed", e);
        } finally {
          set({ user: null, isAuthenticated: false, error: null, isLoading: false });
        }
      },

      fetchProfile: async () => {
        set({ isLoading: true, error: null });
        try {
          const supabase = createClient();
          const { data: { session } } = await supabase.auth.getSession();
          if (!session) {
            set({ isAuthenticated: false, isLoading: false, user: null });
            return;
          }
          const profile = await authApi.getProfile();
          set({ user: profile, isAuthenticated: true, isLoading: false });
        } catch (err: unknown) {
          console.error("fetchProfile failed:", err);
          if (err instanceof ApiError && err.status === 401) {
            const supabase = createClient();
            await supabase.auth.signOut();
            set({ user: null, isAuthenticated: false, isLoading: false, error: "Session expired. Please log in again." });
          } else {
            set({ isLoading: false, error: "Unable to load profile. Please try again later." });
          }
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({ isAuthenticated: state.isAuthenticated }),
    }
  )
);
