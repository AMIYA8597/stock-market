"use client";

import { TickerStrip } from "./ticker-strip";
import { MarketHeatmap } from "./market-heatmap";
import { AiSummaryPanel } from "./ai-summary-panel";
import { DashboardStats } from "./dashboard-stats";
import { PortfolioMini } from "./portfolio-mini";
import { AlertFeed } from "./alert-feed";

export function DashboardContent() {
  return (
    <div className="space-y-6">
      {/* Row 1: Global Market Ticker */}
      <TickerStrip />

      {/* Row 2: Heatmap (7 cols) + AI Summary (5 cols) */}
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12 lg:col-span-7">
          <MarketHeatmap />
        </div>
        <div className="col-span-12 lg:col-span-5">
          <AiSummaryPanel />
        </div>
      </div>

      {/* Row 3: Stats + Portfolio Mini + Alerts */}
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12 lg:col-span-4">
          <DashboardStats />
        </div>
        <div className="col-span-12 lg:col-span-4">
          <PortfolioMini />
        </div>
        <div className="col-span-12 lg:col-span-4">
          <AlertFeed />
        </div>
      </div>
    </div>
  );
}
