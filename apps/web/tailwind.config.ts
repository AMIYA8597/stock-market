import type { Config } from "tailwindcss";
import preset from "@neuroquant/config/tailwind.preset";

const config: Config = {
  darkMode: ["class"],
  presets: [preset],
  content: [
    "./src/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          base: "var(--bg-base)",
          surface: "var(--bg-surface)",
          elevated: "var(--bg-elevated)",
          overlay: "var(--bg-overlay)",
          border: {
            subtle: "var(--border-subtle)",
            muted: "var(--border-muted)",
            strong: "var(--border-strong)",
          },
          text: {
            primary: "var(--text-primary)",
            secondary: "var(--text-secondary)",
            muted: "var(--text-muted)",
          },
          accent: {
            cyan: "var(--accent-cyan)",
            green: "var(--accent-green)",
            red: "var(--accent-red)",
            amber: "var(--accent-amber)",
            purple: "var(--accent-purple)",
          },
          regime: {
            bull: "var(--regime-bull)",
            bear: "var(--regime-bear)",
            side: "var(--regime-side)",
            crisis: "var(--regime-crisis)",
          },
        },
      },
      fontFamily: {
        sans: ["var(--font-instrument)", "system-ui", "sans-serif"],
        display: ["var(--font-cabinet)", "system-ui", "sans-serif"],
        mono: ["var(--font-berkeley)", "ui-monospace", "monospace"],
      },
      screens: {
        terminal: "1280px",
      },
      gridTemplateColumns: {
        terminal: "var(--terminal-sidebar-width) minmax(0, 1fr) var(--terminal-signal-width)",
      },
      gridTemplateRows: {
        terminal: "var(--terminal-topbar-height) minmax(0, 1fr)",
        "terminal-with-banner": "var(--terminal-topbar-height) auto minmax(0, 1fr)",
      },
      minWidth: {
        terminal: "var(--desktop-min-width)",
      },
      spacing: {
        "layout-gutter": "var(--layout-gutter)",
      },
      boxShadow: {
        "terminal-panel": "0 10px 32px rgba(0, 0, 0, 0.28)",
      },
    },
  },
};

export default config;
