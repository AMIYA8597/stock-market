"use client";

import { useEffect, useRef, useMemo, useState } from "react";
import * as d3 from "d3";
import { Card, CardHeader, CardTitle, cn } from "@neuroquant/ui";

interface HeatmapStock {
  symbol: string;
  name: string;
  sector: string;
  market_cap: number;
  change_pct: number;
}

const SAMPLE_STOCKS: HeatmapStock[] = [
  { symbol: "RELIANCE", name: "Reliance Industries", sector: "Energy", market_cap: 1900000, change_pct: 1.2 },
  { symbol: "TCS", name: "Tata Consultancy", sector: "IT", market_cap: 1400000, change_pct: -0.8 },
  { symbol: "HDFCBANK", name: "HDFC Bank", sector: "Banking", market_cap: 1200000, change_pct: 0.5 },
  { symbol: "INFY", name: "Infosys", sector: "IT", market_cap: 750000, change_pct: -1.5 },
  { symbol: "ICICIBANK", name: "ICICI Bank", sector: "Banking", market_cap: 700000, change_pct: 0.9 },
  { symbol: "HINDUNILVR", name: "Hindustan Unilever", sector: "FMCG", market_cap: 600000, change_pct: -0.3 },
  { symbol: "ITC", name: "ITC Ltd", sector: "FMCG", market_cap: 550000, change_pct: 2.1 },
  { symbol: "SBIN", name: "State Bank of India", sector: "Banking", market_cap: 500000, change_pct: 1.8 },
  { symbol: "BHARTIARTL", name: "Bharti Airtel", sector: "Telecom", market_cap: 480000, change_pct: 0.4 },
  { symbol: "KOTAKBANK", name: "Kotak Mahindra", sector: "Banking", market_cap: 350000, change_pct: -0.6 },
  { symbol: "LT", name: "Larsen & Toubro", sector: "Infrastructure", market_cap: 340000, change_pct: 1.1 },
  { symbol: "AXISBANK", name: "Axis Bank", sector: "Banking", market_cap: 310000, change_pct: 0.7 },
  { symbol: "WIPRO", name: "Wipro", sector: "IT", market_cap: 290000, change_pct: -2.3 },
  { symbol: "SUNPHARMA", name: "Sun Pharma", sector: "Pharma", market_cap: 280000, change_pct: 0.2 },
  { symbol: "TATAMOTORS", name: "Tata Motors", sector: "Auto", market_cap: 260000, change_pct: 3.5 },
  { symbol: "MARUTI", name: "Maruti Suzuki", sector: "Auto", market_cap: 240000, change_pct: -0.9 },
  { symbol: "ONGC", name: "Oil & Natural Gas", sector: "Energy", market_cap: 220000, change_pct: 1.6 },
  { symbol: "NTPC", name: "NTPC Ltd", sector: "Power", market_cap: 210000, change_pct: 0.8 },
  { symbol: "POWERGRID", name: "Power Grid Corp", sector: "Power", market_cap: 190000, change_pct: 0.3 },
  { symbol: "ADANIENT", name: "Adani Enterprises", sector: "Conglomerate", market_cap: 180000, change_pct: -1.2 },
  { symbol: "HCLTECH", name: "HCL Technologies", sector: "IT", market_cap: 400000, change_pct: -0.4 },
  { symbol: "TATASTEEL", name: "Tata Steel", sector: "Metals", market_cap: 170000, change_pct: 2.8 },
  { symbol: "BAJFINANCE", name: "Bajaj Finance", sector: "NBFC", market_cap: 430000, change_pct: -1.0 },
  { symbol: "TITAN", name: "Titan Company", sector: "Consumer", market_cap: 280000, change_pct: 1.4 },
];

function getHeatmapColor(changePct: number): string {
  if (changePct >= 4) return "#00C853";
  if (changePct >= 2) return "#00E676";
  if (changePct >= 0.5) return "#69F0AE";
  if (changePct > -0.5) return "#1C2230";
  if (changePct > -2) return "#FF8A80";
  if (changePct > -4) return "#FF5252";
  return "#D50000";
}

export function MarketHeatmap() {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; stock: HeatmapStock } | null>(null);
  const [viewMode, setViewMode] = useState<"sector" | "market_cap">("sector");

  const hierarchyData = useMemo(() => {
    const sectors = new Map<string, HeatmapStock[]>();
    SAMPLE_STOCKS.forEach((s) => {
      const list = sectors.get(s.sector) ?? [];
      list.push(s);
      sectors.set(s.sector, list);
    });

    return {
      name: "market",
      children: Array.from(sectors.entries()).map(([sector, stocks]) => ({
        name: sector,
        children: stocks.map((s) => ({
          name: s.symbol,
          value: s.market_cap,
          stock: s,
        })),
      })),
    };
  }, []);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = 340;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("width", width).attr("height", height);

    const root = d3
      .hierarchy(hierarchyData)
      .sum((d: any) => d.value || 0)
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

    d3.treemap<any>()
      .size([width, height])
      .paddingOuter(2)
      .paddingInner(1)
      .round(true)(root);

    const leaves = root.leaves();

    const groups = svg
      .selectAll("g")
      .data(leaves)
      .enter()
      .append("g")
      .attr("transform", (d: any) => `translate(${d.x0},${d.y0})`);

    groups
      .append("rect")
      .attr("width", (d: any) => Math.max(0, d.x1 - d.x0))
      .attr("height", (d: any) => Math.max(0, d.y1 - d.y0))
      .attr("rx", 2)
      .attr("fill", (d: any) => getHeatmapColor(d.data.stock?.change_pct ?? 0))
      .attr("fill-opacity", 0.85)
      .style("cursor", "pointer")
      .on("mouseenter", function (event: MouseEvent, d: any) {
        d3.select(this).attr("fill-opacity", 1).attr("stroke", "#00D4FF").attr("stroke-width", 1);
        const rect = container.getBoundingClientRect();
        setTooltip({
          x: event.clientX - rect.left,
          y: event.clientY - rect.top,
          stock: d.data.stock,
        });
      })
      .on("mouseleave", function () {
        d3.select(this).attr("fill-opacity", 0.85).attr("stroke", "none");
        setTooltip(null);
      });

    groups
      .filter((d: any) => (d.x1 - d.x0) > 45 && (d.y1 - d.y0) > 30)
      .append("text")
      .attr("x", 4)
      .attr("y", 14)
      .text((d: any) => d.data.name)
      .attr("fill", "#E8EAED")
      .attr("font-size", "10px")
      .attr("font-weight", "600")
      .attr("font-family", "var(--font-jetbrains)");

    groups
      .filter((d: any) => (d.x1 - d.x0) > 45 && (d.y1 - d.y0) > 45)
      .append("text")
      .attr("x", 4)
      .attr("y", 28)
      .text((d: any) => {
        const pct = d.data.stock?.change_pct ?? 0;
        return `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
      })
      .attr("fill", "#E8EAED")
      .attr("fill-opacity", 0.8)
      .attr("font-size", "9px")
      .attr("font-family", "var(--font-jetbrains)");
  }, [hierarchyData]);

  return (
    <Card noPadding className="relative overflow-hidden">
      <CardHeader className="px-4 pt-4">
        <CardTitle>Market Heatmap</CardTitle>
        <div className="flex gap-1">
          {(["sector", "market_cap"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={cn(
                "rounded-nq px-2.5 py-1 text-[10px] font-medium transition-colors",
                viewMode === mode
                  ? "bg-nq-accent/10 text-nq-accent"
                  : "text-nq-text-tertiary hover:text-nq-text-secondary"
              )}
            >
              {mode === "sector" ? "By Sector" : "By Cap"}
            </button>
          ))}
        </div>
      </CardHeader>
      <div ref={containerRef} className="relative px-2 pb-2">
        <svg ref={svgRef} />
        {tooltip && (
          <div
            className="pointer-events-none absolute z-10 rounded-nq border border-nq-border bg-nq-bg-elevated px-3 py-2 shadow-nq-elevated"
            style={{ left: tooltip.x + 12, top: tooltip.y - 10 }}
          >
            <div className="font-mono text-xs font-bold text-nq-text-primary">
              {tooltip.stock.symbol}
            </div>
            <div className="text-[10px] text-nq-text-secondary">{tooltip.stock.name}</div>
            <div className={cn("font-mono text-xs font-medium mt-1", tooltip.stock.change_pct >= 0 ? "text-nq-bull" : "text-nq-bear")}>
              {tooltip.stock.change_pct >= 0 ? "▲" : "▼"} {tooltip.stock.change_pct >= 0 ? "+" : ""}{tooltip.stock.change_pct.toFixed(2)}%
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
