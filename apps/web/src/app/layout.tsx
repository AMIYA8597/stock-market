import type { Metadata, Viewport } from "next";
import { Instrument_Sans, Manrope, Space_Mono } from "next/font/google";
import { Providers } from "@/lib/providers";
import "./globals.css";

const berkeleyMonoFallback = Space_Mono({
  subsets: ["latin"],
  variable: "--font-berkeley",
  display: "swap",
  weight: ["400", "700"],
});

const instrumentSans = Instrument_Sans({
  subsets: ["latin"],
  variable: "--font-instrument",
  display: "swap",
});

const cabinetGroteskFallback = Manrope({
  subsets: ["latin"],
  variable: "--font-cabinet",
  display: "swap",
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
      className={`dark ${berkeleyMonoFallback.variable} ${instrumentSans.variable} ${cabinetGroteskFallback.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-nq-bg-primary antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
