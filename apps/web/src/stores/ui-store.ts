import { create } from "zustand";

interface UIStore {
  sidebarCollapsed: boolean;
  mobileSidebarOpen: boolean;
  commandPaletteOpen: boolean;
  themeMode: "dark" | "light";
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  openMobileSidebar: () => void;
  closeMobileSidebar: () => void;
  toggleMobileSidebar: () => void;
  openCommandPalette: () => void;
  closeCommandPalette: () => void;
  setThemeMode: (mode: "dark" | "light") => void;
  toggleThemeMode: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarCollapsed: false,
  mobileSidebarOpen: false,
  commandPaletteOpen: false,
  themeMode: "dark",
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  openMobileSidebar: () => set({ mobileSidebarOpen: true }),
  closeMobileSidebar: () => set({ mobileSidebarOpen: false }),
  toggleMobileSidebar: () => set((s) => ({ mobileSidebarOpen: !s.mobileSidebarOpen })),
  openCommandPalette: () => set({ commandPaletteOpen: true }),
  closeCommandPalette: () => set({ commandPaletteOpen: false }),
  setThemeMode: (mode) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("nq-theme", mode);
    }
    if (typeof document !== "undefined") {
      document.documentElement.classList.remove("dark", "light");
      document.documentElement.classList.add(mode);
    }
    set({ themeMode: mode });
  },
  toggleThemeMode: () =>
    set((state) => {
      const next = state.themeMode === "dark" ? "light" : "dark";
      if (typeof window !== "undefined") {
        window.localStorage.setItem("nq-theme", next);
      }
      if (typeof document !== "undefined") {
        document.documentElement.classList.remove("dark", "light");
        document.documentElement.classList.add(next);
      }
      return { themeMode: next };
    }),
}));
