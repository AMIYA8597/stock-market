import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'NeuroQuant — Institutional AI Stock Market Platform',
  description: 'Production-grade AI-powered stock market platform for NSE/NIFTY with advanced ML prediction and risk management',
  keywords: ['stock market', 'AI', 'trading', 'predictions', 'NSE', 'NIFTY'],
  authors: [{ name: 'NeuroQuant', url: 'https://neuroquant.app' }],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
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