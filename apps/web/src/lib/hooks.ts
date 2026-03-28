'use client';

import React from 'react';

/**
 * Utility function to combine class names
 * This is already implemented, just adding for completeness
 */
export function classNames(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

/**
 * Theme provider configuration
 */
export const themeConfig = {
  colors: {
    // Base colors
    bgBase: 'var(--bg-base)',
    bgSurface: 'var(--bg-surface)',
    bgElevated: 'var(--bg-elevated)',
    bgOverlay: 'var(--bg-overlay)',

    // Text colors
    textPrimary: 'var(--text-primary)',
    textSecondary: 'var(--text-secondary)',
    textMuted: 'var(--text-muted)',

    // Border colors
    borderSubtle: 'var(--border-subtle)',
    borderMuted: 'var(--border-muted)',
    borderStrong: 'var(--border-strong)',

    // Accent colors
    accentCyan: 'var(--accent-cyan)',
    accentGreen: 'var(--accent-green)',
    accentRed: 'var(--accent-red)',
    accentAmber: 'var(--accent-amber)',
    accentPurple: 'var(--accent-purple)',

    // Regime colors
    regimeBull: 'var(--regime-bull)',
    regimeBear: 'var(--regime-bear)',
    regimeSide: 'var(--regime-side)',
    regimeCrisis: 'var(--regime-crisis)',
  },

  fonts: {
    berkeley: 'var(--font-berkeley)',
    cabinet: 'var(--font-cabinet)',
    instrument: 'var(--font-instrument)',
  },

  spacing: {
    xs: '4px',
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '24px',
    '2xl': '32px',
  },

  borderRadius: {
    sm: '4px',
    md: '8px',
    lg: '12px',
    xl: '16px',
  },

  breakpoints: {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px',
  },
};

/**
 * Responsive breakpoint hooks
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = React.useState(false);

  React.useEffect(() => {
    const media = window.matchMedia(query);
    if (media.matches !== matches) {
      setMatches(media.matches);
    }

    const listener = () => setMatches(media.matches);
    media.addEventListener('change', listener);
    return () => media.removeEventListener('change', listener);
  }, [matches, query]);

  return matches;
}

export function useIsMobile(): boolean {
  return useMediaQuery(`(max-width: ${themeConfig.breakpoints.md})`);
}

export function useIsTablet(): boolean {
  return useMediaQuery(
    `(min-width: ${themeConfig.breakpoints.md}) and (max-width: ${themeConfig.breakpoints.lg})`
  );
}

export function useIsDesktop(): boolean {
  return useMediaQuery(`(min-width: ${themeConfig.breakpoints.lg})`);
}

/**
 * Debounce hook for performance optimization
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = React.useState<T>(value);

  React.useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Throttle hook for performance optimization
 */
export function useThrottle<T>(value: T, interval: number): T {
  const [throttledValue, setThrottledValue] = React.useState<T>(value);
  const lastUpdatedRef = React.useRef(Date.now());

  React.useEffect(() => {
    const now = Date.now();
    if (now >= lastUpdatedRef.current + interval) {
      lastUpdatedRef.current = now;
      setThrottledValue(value);
    }
  }, [value, interval]);

  return throttledValue;
}

/**
 * Local storage hook
 */
export function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T | ((val: T) => T)) => void] {
  const [storedValue, setStoredValue] = React.useState<T>(() => {
    try {
      const item = typeof window !== 'undefined' ? window.localStorage.getItem(key) : null;
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = (value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      }
    } catch (error) {
      console.error(`Error in useLocalStorage: ${error}`);
    }
  };

  return [storedValue, setValue];
}
