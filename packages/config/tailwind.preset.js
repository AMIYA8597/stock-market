/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        nq: {
          bg: {
            primary: "var(--nq-bg-primary)",
            secondary: "var(--nq-bg-secondary)",
            card: "var(--nq-bg-card)",
            elevated: "var(--nq-bg-elevated)",
          },
          border: {
            DEFAULT: "var(--nq-border)",
            hover: "var(--nq-border-hover)",
          },
          accent: {
            DEFAULT: "var(--nq-accent)",
            hover: "var(--nq-accent-hover)",
            muted: "var(--nq-accent-muted)",
          },
          bull: {
            DEFAULT: "var(--nq-bull)",
            muted: "var(--nq-bull-muted)",
            bg: "var(--nq-bull-bg)",
          },
          bear: {
            DEFAULT: "var(--nq-bear)",
            muted: "var(--nq-bear-muted)",
            bg: "var(--nq-bear-bg)",
          },
          warning: {
            DEFAULT: "var(--nq-warning)",
            muted: "var(--nq-warning-muted)",
          },
          text: {
            primary: "var(--nq-text-primary)",
            secondary: "var(--nq-text-secondary)",
            tertiary: "var(--nq-text-tertiary)",
          },
        },
      },
      fontFamily: {
        display: ["var(--font-clash-display)", "system-ui", "sans-serif"],
        body: ["var(--font-cabinet)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains)", "Menlo", "monospace"],
      },
      fontSize: {
        "price-lg": ["2.25rem", { lineHeight: "1", fontWeight: "600" }],
        "price-md": ["1.5rem", { lineHeight: "1", fontWeight: "600" }],
        "price-sm": ["0.875rem", { lineHeight: "1", fontWeight: "500" }],
      },
      borderRadius: {
        nq: "0.5rem",
        "nq-lg": "0.75rem",
        "nq-xl": "1rem",
      },
      boxShadow: {
        "nq-card": "0 1px 3px 0 rgba(0, 0, 0, 0.3), 0 1px 2px -1px rgba(0, 0, 0, 0.3)",
        "nq-elevated": "0 4px 12px 0 rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.3)",
        "nq-glow": "0 0 20px rgba(0, 212, 255, 0.15)",
      },
      animation: {
        "ticker-scroll": "ticker-scroll 30s linear infinite",
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fade-in 0.2s ease-out",
        "slide-up": "slide-up 0.3s ease-out",
        "slide-down": "slide-down 0.3s ease-out",
      },
      keyframes: {
        "ticker-scroll": {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-down": {
          "0%": { opacity: "0", transform: "translateY(-10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      gridTemplateColumns: {
        dashboard: "repeat(12, minmax(0, 1fr))",
      },
    },
  },
  plugins: [],
};
