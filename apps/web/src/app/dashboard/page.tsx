'use client';

import { Suspense } from 'react';
import Header from '@/components/common/Header';
import TickerStrip from '@/components/dashboard/TickerStrip';
import SectorHeatmap from '@/components/dashboard/Heatmap';
import AISummaryPanel from '@/components/dashboard/AISummaryPanel';
import StatCard from '@/components/dashboard/StatCard';
import TopHoldingsCard from '@/components/dashboard/TopHoldingsCard';
import AlertsFeed from '@/components/dashboard/AlertsFeed';
import { StatCardData } from '@/types/market';

/**
 * Dashboard Page - Command Center
 * 
 * Layout: CSS Grid, 12-column, 3 rows
 * 
 * Row 1 — Global Market Ticker (full width):
 *   - WebSocket live price strip: Nifty50 | Sensex | S&P500 | NASDAQ | Gold | BTC | USD/INR
 *   - Smooth horizontal scroll animation
 *   - Color-coded +/- with sparkline mini-chart (SVG, 20-bar)
 * 
 * Row 2 — Market Heatmap (7 cols) + AI Summary Panel (5 cols):
 *   - Market Heatmap (D3.js Treemap style)
 *   - AI Summary Panel with regime, catalysts, fear/greed
 * 
 * Row 3 — 4 stat cards + Portfolio mini + Alerts feed:
 *   - Stat Cards: Portfolio P&L Today | Active Signals | Model Accuracy (30d) | Alerts
 *   - Top Holdings: Donut chart (holdings by sector) + top 5 positions
 *   - Alert Feed: Real-time WebSocket alert stream with severity badges
 */

const statCardsData: StatCardData[] = [
  {
    label: 'Portfolio P&L Today',
    value: 45250,
    change: 45250,
    changePct: 3.25,
    icon: '📈',
    trend: 'up',
  },
  {
    label: 'Active Signals',
    value: 12,
    changePct: 8.5,
    trend: 'up',
    icon: '🎯',
  },
  {
    label: 'Model Accuracy (30d)',
    value: '72.4%',
    changePct: 2.1,
    trend: 'up',
    icon: '🤖',
  },
  {
    label: 'Pending Alerts',
    value: 5,
    changePct: -12.3,
    trend: 'down',
    icon: '🔔',
  },
];

// Loading skeleton component
const SkeletonCard = () => (
  <div className="bg-[#161B24] border border-[#1E2532] rounded-lg p-6 animate-pulse">
    <div className="h-4 bg-[#1E2532] rounded w-24 mb-4" />
    <div className="h-8 bg-[#1E2532] rounded w-40 mb-4" />
    <div className="h-4 bg-[#1E2532] rounded w-32" />
  </div>
);

const DashboardPage = (): JSX.Element => {
  return (
    <div className="min-h-screen bg-[#0A0B0E]">
      {/* Header */}
      <Header />

      <main className="flex-1">
        {/* Row 1: Global Market Ticker (full width) */}
        <Suspense fallback={<div className="h-24 bg-[#0A0B0E] border-b border-[#1E2532]" />}>
          <TickerStrip />
        </Suspense>

        {/* Row 2: Market Heatmap + AI Summary Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 max-w-7xl mx-auto">
          {/* Market Heatmap (7 cols) */}
          <div className="lg:col-span-7">
            <Suspense fallback={<SkeletonCard />}>
              <SectorHeatmap />
            </Suspense>
          </div>

          {/* AI Summary Panel (5 cols) */}
          <div className="lg:col-span-5">
            <Suspense fallback={<SkeletonCard />}>
              <AISummaryPanel />
            </Suspense>
          </div>
        </div>

        {/* Row 3: Stat Cards + Top Holdings + Alert Feed */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 p-6 max-w-7xl mx-auto mb-6">
          {/* 4 Stat Cards */}
          {statCardsData.map((stat, index) => (
            <Suspense key={index} fallback={<SkeletonCard />}>
              <StatCard data={stat} />
            </Suspense>
          ))}
        </div>

        {/* Row 4: Top Holdings + Alert Feed */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6 max-w-7xl mx-auto pb-12">
          {/* Top Holdings (2 cols) */}
          <div className="lg:col-span-2">
            <Suspense fallback={<SkeletonCard />}>
              <TopHoldingsCard />
            </Suspense>
          </div>

          {/* Alert Feed (1 col) */}
          <div className="lg:col-span-1">
            <Suspense fallback={<SkeletonCard />}>
              <AlertsFeed />
            </Suspense>
          </div>
        </div>
      </main>
    </div>
  );
};

export default DashboardPage;
