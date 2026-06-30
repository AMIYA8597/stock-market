"use client";

import ChartSection from "@/components/terminal/ChartSection";
import SignalPanel from "@/components/terminal/SignalPanel";
import TerminalLayout from "@/components/terminal/TerminalLayout";
import TopBar from "@/components/terminal/TopBar";
import Watchlist from "@/components/terminal/Watchlist";
import { useTerminalData } from "@/hooks/useTerminalData";

export default function RootPage(): JSX.Element {
  const { selectedSignal, selectedSymbol, watchlistSignals, loading, refreshing, signalStreamStatus, error, setSelectedSymbol } = useTerminalData();

  return (
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
      watchlist={<Watchlist signals={watchlistSignals} selectedSymbol={selectedSymbol} onSelectSymbol={setSelectedSymbol} />}
      chartSection={<ChartSection signal={selectedSignal} onSelectSymbol={setSelectedSymbol} />}
      signalPanel={<SignalPanel signal={selectedSignal} />}
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
  );
}
