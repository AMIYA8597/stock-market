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
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
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
