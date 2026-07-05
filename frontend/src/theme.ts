import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react';

// Theme interface
export interface ThemeContextProps {
  mode: 'dark' | 'light';
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextProps | undefined>(undefined);

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
  const [mode, setMode] = useState<'dark' | 'light'>('dark');

  const toggle = () => setMode(prev => (prev === 'dark' ? 'light' : 'dark'));

  // Apply a data attribute for CSS selectors if needed
  useEffect(() => {
    document.body.dataset.theme = mode;
  }, [mode]);

  return (
    <ThemeContext.Provider value={{ mode, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextProps => {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
};
