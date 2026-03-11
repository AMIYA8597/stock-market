"use client";

import { Brain, TrendingUp, AlertTriangle, Newspaper } from "lucide-react";
import { Card, CardHeader, CardTitle, RegimeBadge, Badge, cn } from "@neuroquant/ui";

interface CatalystEvent {
  title: string;
  impact: "positive" | "negative" | "neutral";
  source: string;
}

const CATALYSTS: CatalystEvent[] = [
  { title: "RBI holds repo rate at 6.5%, dovish stance maintained", impact: "positive", source: "Reuters" },
  { title: "US CPI comes in at 3.1% YoY, above expectations", impact: "negative", source: "Bloomberg" },
  { title: "Tata Motors EV division reports 40% QoQ growth", impact: "positive", source: "NSE" },
];

function FearGreedGauge({ value }: { value: number }) {
  const rotation = (value / 100) * 180 - 90;
  const label = value >= 75 ? "Extreme Greed" : value >= 55 ? "Greed" : value >= 45 ? "Neutral" : value >= 25 ? "Fear" : "Extreme Fear";
  const color = value >= 55 ? "var(--nq-bull)" : value >= 45 ? "var(--nq-warning)" : "var(--nq-bear)";

  return (
    <div className="flex flex-col items-center gap-1">
      <svg viewBox="0 0 120 70" className="w-28 h-16">
        {/* Background arc */}
        <path
          d="M 10 60 A 50 50 0 0 1 110 60"
          fill="none"
          stroke="var(--nq-border)"
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Colored arc segments */}
        <path d="M 10 60 A 50 50 0 0 1 35 18" fill="none" stroke="var(--nq-bear)" strokeWidth="8" strokeLinecap="round" strokeOpacity="0.6" />
        <path d="M 35 18 A 50 50 0 0 1 60 10" fill="none" stroke="var(--nq-warning)" strokeWidth="8" strokeLinecap="round" strokeOpacity="0.6" />
        <path d="M 60 10 A 50 50 0 0 1 85 18" fill="none" stroke="var(--nq-warning)" strokeWidth="8" strokeLinecap="round" strokeOpacity="0.6" />
        <path d="M 85 18 A 50 50 0 0 1 110 60" fill="none" stroke="var(--nq-bull)" strokeWidth="8" strokeLinecap="round" strokeOpacity="0.6" />
        {/* Needle */}
        <line
          x1="60"
          y1="60"
          x2={60 + 40 * Math.cos((rotation * Math.PI) / 180)}
          y2={60 + 40 * Math.sin((rotation * Math.PI) / 180)}
          stroke={color}
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <circle cx="60" cy="60" r="4" fill={color} />
      </svg>
      <div className="text-center">
        <span className="font-mono text-lg font-bold" style={{ color }}>{value}</span>
        <div className="text-[10px] text-nq-text-tertiary">{label}</div>
      </div>
    </div>
  );
}

export function AiSummaryPanel() {
  return (
    <Card className="flex flex-col gap-4 h-full">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-nq-accent" />
          <CardTitle>NeuroQuant AI Market Pulse</CardTitle>
        </div>
        <Badge variant="accent">Live</Badge>
      </CardHeader>

      {/* Regime + VIX */}
      <div className="flex items-center justify-between">
        <RegimeBadge regime="bull" confidence={72} />
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-nq-text-tertiary">India VIX</span>
          <span className="font-mono text-sm font-semibold text-nq-warning">14.82</span>
          <Badge variant="warning">Z: 0.3</Badge>
        </div>
      </div>

      {/* AI Analysis */}
      <div className="space-y-2 text-xs text-nq-text-secondary leading-relaxed">
        <p>
          Markets are displaying strong momentum with broad-based buying across large-caps.
          The Nifty50 has broken above the key 22,400 resistance with high conviction. Banking
          sector leads with HDFC Bank and ICICI Bank hitting fresh intraday highs.
        </p>
        <p>
          IT sector remains under pressure following US CPI data, with Infosys and Wipro
          facing selling pressure. The regime model maintains a BULL state with 72% confidence,
          though cross-asset correlations show early signs of divergence.
        </p>
      </div>

      {/* Fear & Greed Gauge */}
      <div className="flex items-center justify-center border-t border-nq-border pt-3">
        <FearGreedGauge value={62} />
      </div>

      {/* Top Catalysts */}
      <div className="border-t border-nq-border pt-3">
        <h4 className="mb-2 text-[10px] font-medium text-nq-text-tertiary uppercase tracking-wider">
          Top Catalysts
        </h4>
        <div className="space-y-2">
          {CATALYSTS.map((event, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <div className={cn(
                "mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full",
                event.impact === "positive" ? "bg-nq-bull-bg" : event.impact === "negative" ? "bg-nq-bear-bg" : "bg-nq-bg-elevated"
              )}>
                {event.impact === "positive" ? (
                  <TrendingUp className="h-2.5 w-2.5 text-nq-bull" />
                ) : event.impact === "negative" ? (
                  <AlertTriangle className="h-2.5 w-2.5 text-nq-bear" />
                ) : (
                  <Newspaper className="h-2.5 w-2.5 text-nq-text-tertiary" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-nq-text-primary leading-tight">{event.title}</p>
                <span className="text-[10px] text-nq-text-tertiary">{event.source}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
