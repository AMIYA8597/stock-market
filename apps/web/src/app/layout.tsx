import type { Metadata, Viewport } from "next";
import Script from "next/script";
import { ThemeSync } from "@/components/common/theme-sync";
import { Providers } from "@/lib/providers";
import "./globals.css";

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
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
    apple: "/favicon.svg",
  },
  openGraph: {
    title: "NeuroQuant — AI Stock Market Intelligence",
    description:
      "Institutional-grade AI-powered stock market analysis platform with real-time predictions, risk management, and portfolio optimization.",
    type: "website",
  },
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
    <html lang="en" suppressHydrationWarning>
      <head>
        <Script id="nq-theme-init" strategy="beforeInteractive">
          {`(function(){try{var t=localStorage.getItem('nq-theme');var m=t==='light'?'light':'dark';document.documentElement.classList.remove('dark','light');document.documentElement.classList.add(m);}catch(e){document.documentElement.classList.add('dark');}})();`}
        </Script>
      </head>
      <body className="min-h-screen bg-nq-bg-primary antialiased">
        <Providers>
          <ThemeSync />
          {children}
        </Providers>
      </body>
    </html>
  );
}
