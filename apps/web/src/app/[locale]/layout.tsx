import type { Metadata, Viewport } from "next";
import Script from "next/script";
import { ThemeSync } from "@/components/common/theme-sync";
import { GlobalToast } from "@/components/common/global-toast";
import { Providers } from "@/lib/providers";
import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import "../globals.css";

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

export default async function RootLayout({
  children,
  params: { locale },
}: {
  children: React.ReactNode;
  params: { locale: string };
}) {
  const messages = await getMessages();
  return (
    <html lang={locale} suppressHydrationWarning>
      <head>
        <Script id="nq-theme-init" strategy="beforeInteractive">
          {`(function(){try{var t=localStorage.getItem('nq-theme');var m=t==='light'?'light':'dark';document.documentElement.classList.remove('dark','light');document.documentElement.classList.add(m);}catch(e){document.documentElement.classList.add('dark');}})();`}
        </Script>
      </head>
      <body className="min-h-screen bg-nq-bg-primary antialiased">
        <Providers>
          <NextIntlClientProvider messages={messages}>
            <ThemeSync />
            {children}
            <GlobalToast />
          </NextIntlClientProvider>
        </Providers>
      </body>
    </html>
  );
}
