"use client";

import ChartSection from "@/components/terminal/ChartSection";
import SignalPanel from "@/components/terminal/SignalPanel";
import TopBar from "@/components/terminal/TopBar";
import Watchlist from "@/components/terminal/Watchlist";
import { useTerminalData } from "@/hooks/useTerminalData";

export default function TerminalPage(): JSX.Element {
  const { selectedSignal, selectedSymbol, watchlistSignals, loading, refreshing, signalStreamStatus, error, setSelectedSymbol } = useTerminalData();

  return (
    <main className="relative grid min-h-screen grid-cols-1 grid-rows-[auto_auto_1fr_auto] overflow-x-hidden bg-[var(--nq-bg-base)] md:grid-rows-[auto_auto_1fr_auto] lg:h-screen lg:grid-cols-[280px_1fr_320px] lg:grid-rows-[auto_1fr] lg:overflow-hidden">
      <TopBar selectedSignal={selectedSignal} refreshing={refreshing} signalStreamStatus={signalStreamStatus} />

      {error ? (
        <div className="col-span-1 border-b border-[rgba(255,59,92,0.35)] bg-[rgba(255,59,92,0.10)] px-3 py-2 text-xs text-[#FF3B5C] lg:col-span-3">
          Terminal feed degraded: {error}
        </div>
      ) : null}

      <Watchlist
        signals={watchlistSignals}
        selectedSymbol={selectedSymbol}
        onSelectSymbol={setSelectedSymbol}
      />
      <ChartSection signal={selectedSignal} />
      <SignalPanel signal={selectedSignal} />

      {loading && watchlistSignals.length === 0 ? (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-[rgba(7,9,15,0.45)]">
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-2 text-sm text-[var(--nq-text-secondary)]">
            Loading terminal feed...
          </div>
        </div>
      ) : null}

      {error ? (
        <div className="pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2 rounded border border-[rgba(255,59,92,0.4)] bg-[rgba(255,59,92,0.12)] px-3 py-1 text-xs text-[#FF3B5C]">
          {error}
        </div>
      ) : null}
    </main>
  );
}
