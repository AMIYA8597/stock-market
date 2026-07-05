// src/components/ui/DarkModeToggle.tsx
"use client";

import { useEffect, useState } from "react";

export default function DarkModeToggle() {
  const [isDark, setIsDark] = useState<boolean>(false);

  // Initialize from system preference or previous setting in localStorage
  useEffect(() => {
    const stored = localStorage.getItem("theme");
    if (stored) {
      setIsDark(stored === "dark");
    } else {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      setIsDark(prefersDark);
    }
  }, []);

  // Apply theme to root element whenever it changes
  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.setAttribute("data-theme", "dark");
      root.style.setProperty("color-scheme", "dark");
      localStorage.setItem("theme", "dark");
    } else {
      root.setAttribute("data-theme", "light");
      root.style.setProperty("color-scheme", "light");
      localStorage.setItem("theme", "light");
    }
  }, [isDark]);

  return (
    <button
      onClick={() => setIsDark(!isDark)}
      className="rounded px-2 py-1 text-sm border border-[var(--nq-border)] bg-[var(--nq-bg-card)] text-[var(--nq-text-primary)] hover:bg-[var(--nq-bg-card-hover)]"
    >
      {isDark ? "☀️ Light" : "🌙 Dark"}
    </button>
  );
}
