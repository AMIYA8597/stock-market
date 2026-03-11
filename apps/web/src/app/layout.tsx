<<<<<<< HEAD
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'NeuroQuant — Institutional AI Stock Market Platform',
  description: 'Production-grade AI-powered stock market platform for NSE/NIFTY with advanced ML prediction and risk management',
  keywords: ['stock market', 'AI', 'trading', 'predictions', 'NSE', 'NIFTY'],
  authors: [{ name: 'NeuroQuant', url: 'https://neuroquant.app' }],
=======
import type { Metadata, Viewport } from "next";
import { JetBrains_Mono } from "next/font/google";
import localFont from "next/font/local";
import { Providers } from "@/lib/providers";
import "./globals.css";

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

const clashDisplay = localFont({
  src: [
    { path: "../fonts/ClashDisplay-Variable.woff2", style: "normal" },
  ],
  variable: "--font-clash-display",
  display: "swap",
  fallback: ["system-ui", "sans-serif"],
});

const cabinetGrotesk = localFont({
  src: [
    { path: "../fonts/CabinetGrotesk-Variable.woff2", style: "normal" },
  ],
  variable: "--font-cabinet",
  display: "swap",
  fallback: ["system-ui", "sans-serif"],
});

export const metadata: Metadata = {
  title: {
    default: "NeuroQuant — AI Stock Market Intelligence",
    template: "%s | NeuroQuant",
  },
  description:
    "Institutional-grade AI-powered stock market analysis platform with real-time predictions, risk management, and portfolio optimization.",
  keywords: [
    "stock market",
    "AI trading",
    "quantitative finance",
    "portfolio optimization",
    "machine learning",
    "risk management",
  ],
};

export const viewport: Viewport = {
  themeColor: "#0A0B0E",
  width: "device-width",
  initialScale: 1,
>>>>>>> 10e1aa79ae3f95f38345cbdf853c86957900630c
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
<<<<<<< HEAD
    <html lang="en">
      <head>
        {/* Google Fonts: Clash Display for headings */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=Clash+Display:wght@400;600;700&display=swap"
          rel="stylesheet"
        />
        {/* JetBrains Mono for monospace/numbers */}
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
        {/* Cabinet Grotesk for body text */}
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
=======
    <html
      lang="en"
      className={`dark ${jetbrainsMono.variable} ${clashDisplay.variable} ${cabinetGrotesk.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-nq-bg-primary antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
>>>>>>> 10e1aa79ae3f95f38345cbdf853c86957900630c
