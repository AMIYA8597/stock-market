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
  const [timelineStep, setTimelineStep] = useState<number>(100);
  const [systemicRiskMode, setSystemicRiskMode] = useState<boolean>(false);
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

  const selectedNeighborSet = useMemo(() => {
    const neighbors = new Set<string>([selectedTicker]);
    for (const edge of graph?.edges ?? []) {
      if (edge.source === selectedTicker) {
        neighbors.add(edge.target);
      }
      if (edge.target === selectedTicker) {
        neighbors.add(edge.source);
      }
    }
    return neighbors;
  }, [graph?.edges, selectedTicker]);

  const degreeMap = useMemo(() => {
    const map = new Map<string, number>();
    for (const node of graph?.nodes ?? []) {
      map.set(node.ticker, 0);
    }
    for (const edge of graph?.edges ?? []) {
      map.set(edge.source, (map.get(edge.source) ?? 0) + 1);
      map.set(edge.target, (map.get(edge.target) ?? 0) + 1);
    }
    return map;
  }, [graph?.edges, graph?.nodes]);

  const maxDegree = useMemo(() => {
    return Math.max(1, ...Array.from(degreeMap.values()));
  }, [degreeMap]);

  const graphSlice = useMemo(() => {
    const nodes = graph?.nodes ?? [];
    const edges = graph?.edges ?? [];
    const limit = Math.max(1, Math.floor((timelineStep / 100) * edges.length));
    return {
      nodes,
      edges: edges.slice(0, limit),
    };
  }, [graph?.edges, graph?.nodes, timelineStep]);

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
          <label htmlFor="timeline-step">Timeline</label>
          <input
            id="timeline-step"
            type="range"
            min={10}
            max={100}
            step={5}
            value={timelineStep}
            onChange={(event) => setTimelineStep(Number(event.target.value))}
            className="w-24"
          />
          <button
            type="button"
            onClick={() => setSystemicRiskMode((prev) => !prev)}
            className={`rounded border px-2 py-1 ${systemicRiskMode ? "border-[var(--nq-accent-cyan)] bg-[rgba(0,212,245,0.10)] text-[var(--nq-text-primary)]" : "border-[var(--nq-border)] text-[var(--nq-text-secondary)]"}`}
          >
            Systemic Risk
          </button>
        </div>
      </div>

      {error ? <p className="text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
        <div className="relative h-[420px] overflow-hidden rounded-lg border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4 sm:h-[480px]">
          <svg className="h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Correlation network">
            {graphSlice.edges.map((edge) => {
              const sourceNode = nodeByTicker.get(edge.source);
              const targetNode = nodeByTicker.get(edge.target);
              if (!sourceNode || !targetNode) {
                return null;
              }
              const isSelected = edge.source === selectedTicker || edge.target === selectedTicker;
              const isInEgo = selectedNeighborSet.has(edge.source) && selectedNeighborSet.has(edge.target);
              return (
                <line
                  key={`${edge.source}-${edge.target}`}
                  x1={sourceNode.x}
                  y1={sourceNode.y}
                  x2={targetNode.x}
                  y2={targetNode.y}
                  stroke={edge.correlation >= 0.5 ? "rgba(0,230,118,0.50)" : "rgba(255,59,92,0.45)"}
                  strokeWidth={(isSelected ? 0.5 : 0.24) + edge.correlation * 0.8}
                  opacity={isInEgo ? (isSelected ? 0.95 : 0.72) : 0.12}
                />
              );
            })}

            {graphSlice.nodes.map((node) => {
              const isSelected = node.ticker === selectedTicker;
              const isNeighbor = selectedNeighborSet.has(node.ticker);
              const degree = degreeMap.get(node.ticker) ?? 0;
              const degreeScale = degree / maxDegree;
              return (
                <g key={node.ticker} onClick={() => setSelectedTicker(node.ticker)} style={{ cursor: "pointer" }}>
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={Math.max(1.8, node.size / 4.4)}
                    fill={sectorColorMap[node.sector] ?? "rgba(232,237,245,0.74)"}
                    stroke={isSelected ? "rgba(255,255,255,0.95)" : systemicRiskMode ? "rgba(255,255,255,0.45)" : "transparent"}
                    strokeWidth={isSelected ? 0.9 : systemicRiskMode ? 0.25 + degreeScale * 1.5 : 0}
                    opacity={isNeighbor ? 1 : 0.35}
                  />
                  <text x={node.x} y={node.y + node.size / 5 + 2.8} fontSize="2.1" textAnchor="middle" fill={isNeighbor ? "rgba(232,237,245,0.92)" : "rgba(232,237,245,0.35)"}>
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
            <div className="mt-1 text-xs text-[var(--nq-text-secondary)]">Degree centrality: {((degreeMap.get(selectedNode?.ticker ?? "") ?? 0) / maxDegree).toFixed(2)}</div>
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
              <div className="flex items-center justify-between"><span>Edges</span><span>{graphSlice.edges.length}</span></div>
              <div className="flex items-center justify-between"><span>Window</span><span>{graph?.window_days ?? windowDays}d</span></div>
              <div className="flex items-center justify-between"><span>Timeline Replay</span><span>{timelineStep}%</span></div>
            </div>
          </div>
        </aside>
      </div>
    </motion.div>
  );
}
