// Design System for Stock Market UI
// Uses CSS custom properties (variables) for colors, gradients, shadows, and theming.
// Primary palette: cyan‑purple gradient (option 1 as per user selection).
// Dark mode enabled via prefers-color-scheme.

export const designTokens = {
  // Primary colors (cyan‑purple gradient)
  primaryStart: "#00bcd4", // cyan
  primaryEnd: "#9c27b0", // purple

  // Secondary colors
  secondaryStart: "#ff9800", // amber
  secondaryEnd: "#ff5722", // deep orange

  // Neutral palette
  neutral100: "#f5f5f5",
  neutral200: "#eeeeee",
  neutral300: "#e0e0e0",
  neutral400: "#bdbdbd",
  neutral500: "#9e9e9e",
  neutral600: "#757575",
  neutral700: "#616161",
  neutral800: "#424242",
  neutral900: "#212121",

  // Font family
  fontFamily: "'Inter', sans-serif",

  // Shadows
  shadowSm: "0 1px 2px rgba(0,0,0,0.05)",
  shadowMd: "0 4px 6px rgba(0,0,0,0.1)",
  shadowLg: "0 10px 15px rgba(0,0,0,0.15)",

  // Transition timing
  transitionFast: "150ms",
  transitionNormal: "300ms",
  transitionSlow: "500ms",

  // Border radius
  borderRadius: "8px",
};

// Export CSS variable definitions as a string to be injected into the global stylesheet.
export const cssVariables = `
:root {
  --color-primary-start: ${designTokens.primaryStart};
  --color-primary-end: ${designTokens.primaryEnd};
  --color-secondary-start: ${designTokens.secondaryStart};
  --color-secondary-end: ${designTokens.secondaryEnd};
  --color-neutral-100: ${designTokens.neutral100};
  --color-neutral-200: ${designTokens.neutral200};
  --color-neutral-300: ${designTokens.neutral300};
  --color-neutral-400: ${designTokens.neutral400};
  --color-neutral-500: ${designTokens.neutral500};
  --color-neutral-600: ${designTokens.neutral600};
  --color-neutral-700: ${designTokens.neutral700};
  --color-neutral-800: ${designTokens.neutral800};
  --color-neutral-900: ${designTokens.neutral900};
  --font-family: ${designTokens.fontFamily};
  --shadow-sm: ${designTokens.shadowSm};
  --shadow-md: ${designTokens.shadowMd};
  --shadow-lg: ${designTokens.shadowLg};
  --transition-fast: ${designTokens.transitionFast};
  --transition-normal: ${designTokens.transitionNormal};
  --transition-slow: ${designTokens.transitionSlow};
  --border-radius: ${designTokens.borderRadius};
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-primary-start: #9c27b0; /* swap for dark */
    --color-primary-end: #00bcd4;
    --color-neutral-100: var(--color-neutral-900);
    --color-neutral-200: var(--color-neutral-800);
    --color-neutral-300: var(--color-neutral-700);
    --color-neutral-400: var(--color-neutral-600);
    --color-neutral-500: var(--color-neutral-500);
    --color-neutral-600: var(--color-neutral-400);
    --color-neutral-700: var(--color-neutral-300);
    --color-neutral-800: var(--color-neutral-200);
    --color-neutral-900: var(--color-neutral-100);
  }
}`;
