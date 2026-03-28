"use client";

import { useEffect } from "react";

import { useUIStore } from "@/stores/ui-store";

export function ThemeSync(): null {
  const setThemeMode = useUIStore((state) => state.setThemeMode);

  useEffect(() => {
    const stored =
      typeof window !== "undefined"
        ? (window.localStorage.getItem("nq-theme") as "dark" | "light" | null)
        : null;

    const mode = stored === "light" ? "light" : "dark";
    setThemeMode(mode);
  }, [setThemeMode]);

  return null;
}
