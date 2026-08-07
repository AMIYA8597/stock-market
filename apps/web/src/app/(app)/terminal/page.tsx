"use client";

import dynamic from "next/dynamic";
import TopBar from "@/components/terminal/TopBar";
import Watchlist from "@/components/terminal/Watchlist";
import TerminalLayout from "@/components/terminal/TerminalLayout";

const ChartSection = dynamic(() => import("@/components/terminal/ChartSection"), { 
  ssr: false, 
  loading: () => <div className="h-full w-full animate-pulse bg-nq-bg-base/50" /> 
});
const SignalPanel = dynamic(() => import("@/components/terminal/SignalPanel"), { ssr: false });
const PaperTradePanel = dynamic(() => import("@/components/terminal/panes/PaperTradePanel"), { ssr: false });
const AlertsManager = dynamic(() => import("@/components/terminal/panes/AlertsManager"), { ssr: false });
import { useTerminalData } from "@/hooks/useTerminalData";
import { AuthGuard } from "@/components/auth/AuthGuard";

export default function RootPage(): JSX.Element {
  const { selectedSignal, selectedSymbol, watchlistSignals, wlLists, loading, refreshing, signalStreamStatus, error, setSelectedSymbol, addWatchlistSymbol, removeWatchlistSymbol } = useTerminalData();

  return (
    <AuthGuard>
      <TerminalLayout
        selectedSymbol={selectedSymbol}
        topBar={<TopBar selectedSignal={selectedSignal} refreshing={refreshing} signalStreamStatus={signalStreamStatus} />}
        statusBanner={
          <div className="flex w-full items-center justify-between font-mono text-[10px] leading-normal tracking-wide">
            <span className="text-[var(--nq-accent-cyan)]">
              🛡️ <strong>Out-of-Sample CPCV Verified:</strong> Ensemble models are validated across multiple market regimes. Sizing metrics reflect cost-adjusted historical Sharpe ratios.
            </span>
            {error && (
              <span className="ml-4 font-bold text-[#FF3B5C]">
                Feed error: {error}
              </span>
            )}
          </div>
        }
        watchlist={<Watchlist signals={watchlistSignals} wlLists={wlLists} selectedSymbol={selectedSymbol} onSelectSymbol={setSelectedSymbol} onAddSymbol={addWatchlistSymbol} onRemoveSymbol={removeWatchlistSymbol} />}
        chartSection={<ChartSection signal={selectedSignal} onSelectSymbol={setSelectedSymbol} defaultSymbol={selectedSymbol} />}
        signalPanel={<SignalPanel signal={selectedSignal} />}
        paperTradePanel={<PaperTradePanel selectedSymbol={selectedSymbol} />}
        alertsPanel={<AlertsManager />}
        overlay={
          loading && watchlistSignals.length === 0 ? (
            <div className="flex h-full items-center justify-center bg-[rgba(7,9,15,0.45)]">
              <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-2 text-sm text-[var(--nq-text-secondary)]">
                Loading terminal feed...
              </div>
            </div>
          ) : undefined
        }
      />
    </AuthGuard>
  );
}
