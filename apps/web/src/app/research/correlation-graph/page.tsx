"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { contractsApi, type CorrelationGraphResponse } from "@/lib/contracts-api";

const sectorColorMap: Record<string, string> = {
  IT: "rgba(0,212,245,0.78)",
  Banking: "rgba(255,184,0,0.78)",
  Crypto: "rgba(102,255,188,0.76)",
  Index: "rgba(255,129,76,0.74)",
  Energy: "rgba(226,238,250,0.74)",
};

export default function CorrelationGraphPage(): JSX.Element {
  const [windowDays, setWindowDays] = useState<number>(60);
  const [graph, setGraph] = useState<CorrelationGraphResponse | null>(null);
  const [selectedTicker, setSelectedTicker] = useState<string>("RELIANCE.NS");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const stale = useMemo(() => {
    if (!lastUpdated) {
      return true;
    }
    return Date.now() - new Date(lastUpdated).getTime() > 70_000;
  }, [lastUpdated]);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);
      try {
        const response = await contractsApi.getCorrelationGraph(windowDays);
        if (!mounted) {
          return;
        }
        setGraph(response);
        setLastUpdated(new Date().toISOString());
        setSelectedTicker((current) => {
          if (response.nodes.some((item) => item.ticker === current)) {
            return current;
          }
          return response.nodes[0]?.ticker ?? current;
        });
      } catch (requestError) {
        if (!mounted) {
          return;
        }
        const message = requestError instanceof Error ? requestError.message : "Unable to load correlation graph contract.";
        setError(message);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void load();

    const timer = setInterval(() => {
      void load();
    }, 45_000);

    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [windowDays]);

  const nodeByTicker = useMemo(() => new Map((graph?.nodes ?? []).map((node) => [node.ticker, node])), [graph?.nodes]);

  const selectedNode = useMemo(() => {
    return graph?.nodes.find((node) => node.ticker === selectedTicker) ?? null;
  }, [graph?.nodes, selectedTicker]);

  const selectedTopCorrelates = useMemo(() => {
    return (graph?.edges ?? [])
      .filter((edge) => edge.source === selectedTicker || edge.target === selectedTicker)
      .map((edge) => ({
        ticker: edge.source === selectedTicker ? edge.target : edge.source,
        correlation: edge.correlation,
      }))
      .sort((a, b) => b.correlation - a.correlation)
      .slice(0, 6);
  }, [graph?.edges, selectedTicker]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: "easeOut" }}
      className="space-y-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold">Correlation Graph</h2>
        <div className="flex items-center gap-2 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-xs text-[var(--nq-text-secondary)]">
          <span>Updated: {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : "--"}</span>
          <span className="text-[var(--nq-border)]">|</span>
          <span className={stale ? "text-[var(--nq-accent-amber)]" : "text-[var(--nq-accent-green)]"}>{stale ? "stale" : "fresh"}</span>
          <span className="text-[var(--nq-border)]">|</span>
          <label htmlFor="corr-window">Window</label>
          <select
            id="corr-window"
            value={windowDays}
            onChange={(event) => setWindowDays(Number(event.target.value) || 60)}
            className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.03)] px-2 py-1 text-xs"
          >
            <option value={60}>60d</option>
            <option value={90}>90d</option>
            <option value={126}>126d</option>
            <option value={252}>252d</option>
          </select>
        </div>
      </div>

      {error ? <p className="text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
        <div className="relative h-[420px] overflow-hidden rounded-lg border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4 sm:h-[480px]">
          <svg className="h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Correlation network">
            {(graph?.edges ?? []).map((edge) => {
              const sourceNode = nodeByTicker.get(edge.source);
              const targetNode = nodeByTicker.get(edge.target);
              if (!sourceNode || !targetNode) {
                return null;
              }
              const isSelected = edge.source === selectedTicker || edge.target === selectedTicker;
              return (
                <line
                  key={`${edge.source}-${edge.target}`}
                  x1={sourceNode.x}
                  y1={sourceNode.y}
                  x2={targetNode.x}
                  y2={targetNode.y}
                  stroke={edge.correlation >= 0.5 ? "rgba(0,230,118,0.50)" : "rgba(255,59,92,0.45)"}
                  strokeWidth={(isSelected ? 0.5 : 0.24) + edge.correlation * 0.8}
                  opacity={isSelected ? 0.95 : 0.6}
                />
              );
            })}

            {(graph?.nodes ?? []).map((node) => {
              const isSelected = node.ticker === selectedTicker;
              return (
                <g key={node.ticker} onClick={() => setSelectedTicker(node.ticker)} style={{ cursor: "pointer" }}>
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={Math.max(1.8, node.size / 4.4)}
                    fill={sectorColorMap[node.sector] ?? "rgba(232,237,245,0.74)"}
                    stroke={isSelected ? "rgba(255,255,255,0.95)" : "transparent"}
                    strokeWidth={isSelected ? 0.8 : 0}
                  />
                  <text x={node.x} y={node.y + node.size / 5 + 2.8} fontSize="2.1" textAnchor="middle" fill="rgba(232,237,245,0.92)">
                    {node.ticker}
                  </text>
                </g>
              );
            })}
          </svg>

          {loading ? <div className="absolute inset-0 flex items-center justify-center bg-[rgba(7,9,15,0.36)] text-xs text-[var(--nq-text-secondary)]">Loading correlation graph...</div> : null}
        </div>

        <aside className="space-y-3">
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
            <h3 className="mb-2 text-sm font-medium text-[var(--nq-text-secondary)]">Selected Asset</h3>
            <div className="text-sm font-semibold">{selectedNode?.ticker ?? "--"}</div>
            <div className="mt-1 text-xs text-[var(--nq-text-secondary)]">Sector: {selectedNode?.sector ?? "--"}</div>
            <div className="mt-1 text-xs text-[var(--nq-text-secondary)]">Central asset: {graph?.central_asset ?? "--"}</div>
          </div>

          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
            <h3 className="mb-2 text-sm font-medium text-[var(--nq-text-secondary)]">Top Correlates</h3>
            <div className="space-y-2 text-xs">
              {selectedTopCorrelates.map((entry) => (
                <button
                  key={`${selectedTicker}-${entry.ticker}`}
                  onClick={() => setSelectedTicker(entry.ticker)}
                  className="flex w-full items-center justify-between rounded bg-[rgba(255,255,255,0.02)] px-2 py-1 text-left transition hover:bg-[rgba(255,255,255,0.06)]"
                >
                  <span>{entry.ticker}</span>
                  <span>{entry.correlation.toFixed(2)}</span>
                </button>
              ))}
              {!loading && selectedTopCorrelates.length === 0 ? <div className="text-[var(--nq-text-secondary)]">No correlates returned.</div> : null}
            </div>
          </div>

          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
            <h3 className="mb-2 text-sm font-medium text-[var(--nq-text-secondary)]">Contract Summary</h3>
            <div className="space-y-1 text-xs text-[var(--nq-text-secondary)]">
              <div className="flex items-center justify-between"><span>Nodes</span><span>{graph?.nodes.length ?? 0}</span></div>
              <div className="flex items-center justify-between"><span>Edges</span><span>{graph?.edges.length ?? 0}</span></div>
              <div className="flex items-center justify-between"><span>Window</span><span>{graph?.window_days ?? windowDays}d</span></div>
            </div>
          </div>
        </aside>
      </div>
    </motion.div>
  );
}
