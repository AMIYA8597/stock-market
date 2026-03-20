'use client';

import { Suspense, useEffect, useState } from 'react';
import Header from '@/components/common/Header';
import TickerStrip from '@/components/dashboard/TickerStrip';
import SectorHeatmap from '@/components/dashboard/Heatmap';
import AISummaryPanel from '@/components/dashboard/AISummaryPanel';
import StatCard from '@/components/dashboard/StatCard';
import TopHoldingsCard from '@/components/dashboard/TopHoldingsCard';
import AlertsFeed from '@/components/dashboard/AlertsFeed';
import { AmbientLucideBackground } from '@/components/common/ambient-lucide-background';
import { contractsApi } from '@/lib/contracts-api';
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

const loadingStatCardsData: StatCardData[] = [
  {
    label: 'Portfolio P&L Today',
    value: '--',
    changePct: undefined,
    icon: 'P',
    trend: 'neutral',
  },
  {
    label: 'Active Signals',
    value: '--',
    changePct: undefined,
    trend: 'neutral',
    icon: 'S',
  },
  {
    label: 'Model Accuracy (30d)',
    value: '--',
    changePct: undefined,
    trend: 'neutral',
    icon: 'M',
  },
  {
    label: 'Pending Alerts',
    value: '--',
    changePct: undefined,
    trend: 'neutral',
    icon: 'A',
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
  const [statCardsData, setStatCardsData] = useState<StatCardData[]>(loadingStatCardsData);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [statsLastUpdated, setStatsLastUpdated] = useState<number | null>(null);

  useEffect(() => {
    let mounted = true;

    async function loadStats(): Promise<void> {
      try {
        setStatsError(null);
        const [holdings, drifts, modelAccuracy] = await Promise.all([
          contractsApi.getPortfolioHoldings(),
          contractsApi.getDrift(),
          contractsApi.getModelAccuracy(),
        ]);

        if (!mounted) {
          return;
        }

        const totalPnl = holdings.total_unrealized_pnl;
        const totalValue = holdings.holdings.reduce((sum, item) => sum + item.quantity * item.ltp, 0);
        const pnlPct = totalValue > 0 ? (totalPnl / totalValue) * 100 : 0;

        const activeDrifts = drifts.filter((item) => item.drift_detected).length;
        const avgDirectionalAccuracy =
          modelAccuracy.length > 0
            ? modelAccuracy.reduce((sum, item) => sum + item.directional_accuracy, 0) / modelAccuracy.length
            : 0;

        setStatCardsData([
          {
            label: 'Portfolio P&L Today',
            value: totalPnl,
            change: totalPnl,
            changePct: pnlPct,
            icon: 'P',
            trend: totalPnl > 0 ? 'up' : totalPnl < 0 ? 'down' : 'neutral',
          },
          {
            label: 'Active Signals',
            value: holdings.holdings.length,
            changePct: 0,
            trend: holdings.holdings.length > 0 ? 'up' : 'neutral',
            icon: 'S',
          },
          {
            label: 'Model Accuracy (30d)',
            value: `${(avgDirectionalAccuracy * 100).toFixed(1)}%`,
            changePct: 0,
            trend: avgDirectionalAccuracy >= 0.6 ? 'up' : 'neutral',
            icon: 'M',
          },
          {
            label: 'Pending Alerts',
            value: activeDrifts,
            changePct: activeDrifts > 0 ? 100 : 0,
            trend: activeDrifts > 0 ? 'down' : 'neutral',
            icon: 'A',
          },
        ]);
        setStatsLastUpdated(Date.now());
      } catch {
        if (mounted) {
          setStatCardsData(loadingStatCardsData);
          setStatsError('Unable to load dashboard stat contracts.');
        }
      }
    }

    void loadStats();
    const intervalId = setInterval(() => {
      void loadStats();
    }, 45_000);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, []);

  const statsAgeSeconds = statsLastUpdated ? Math.floor((Date.now() - statsLastUpdated) / 1000) : null;
  const statsState =
    statsError !== null ? 'degraded' : statsAgeSeconds !== null && statsAgeSeconds > 90 ? 'stale' : 'fresh';

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#0A0B0E]">
      <AmbientLucideBackground className="opacity-80" />

      {/* Header */}
      <Header />

      <main className="relative z-10 flex-1">
        <div className="mx-auto mt-4 flex max-w-[1320px] items-center justify-end px-4 sm:px-6">
          <span
            className={`rounded border px-2 py-1 text-[10px] uppercase tracking-[0.08em] sm:text-xs ${
              statsState === 'fresh'
                ? 'border-[rgba(0,230,118,0.35)] bg-[rgba(0,230,118,0.10)] text-[#00E676]'
                : statsState === 'stale'
                  ? 'border-[rgba(255,184,0,0.35)] bg-[rgba(255,184,0,0.10)] text-[#FFB800]'
                  : 'border-[rgba(255,59,92,0.35)] bg-[rgba(255,59,92,0.10)] text-[#FF3B5C]'
            }`}
          >
            Stats {statsState}
            {statsAgeSeconds !== null ? ` | ${statsAgeSeconds}s` : ''}
          </span>
        </div>

        {statsError ? (
          <div className="mx-auto mt-4 max-w-[1320px] px-4 sm:px-6">
            <div className="rounded border border-[rgba(255,59,92,0.35)] bg-[rgba(255,59,92,0.10)] px-3 py-2 text-xs text-[#FF3B5C]">
              {statsError}
            </div>
          </div>
        ) : null}

        {/* Row 1: Global Market Ticker (full width) */}
        <Suspense fallback={<div className="h-24 bg-[#0A0B0E] border-b border-[#1E2532]" />}>
          <TickerStrip />
        </Suspense>

        {/* Row 2: Market Heatmap + AI Summary Panel */}
        <div className="mx-auto grid max-w-[1320px] grid-cols-1 gap-4 px-4 py-5 sm:gap-6 sm:px-6 lg:grid-cols-12">
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
        <div className="mx-auto mb-2 grid max-w-[1320px] grid-cols-1 gap-3 px-4 sm:grid-cols-2 sm:gap-4 sm:px-6 lg:grid-cols-4">
          {/* 4 Stat Cards */}
          {statCardsData.map((stat, index) => (
            <Suspense key={index} fallback={<SkeletonCard />}>
              <StatCard data={stat} />
            </Suspense>
          ))}
        </div>

        {/* Row 4: Top Holdings + Alert Feed */}
        <div className="mx-auto grid max-w-[1320px] grid-cols-1 gap-4 px-4 pb-12 pt-4 sm:gap-6 sm:px-6 lg:grid-cols-3">
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
