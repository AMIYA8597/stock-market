"use client";

import { Card, CardHeader, CardTitle, cn, formatPrice, formatPercent, getPriceColor, getDirectionArrow } from "@neuroquant/ui";

interface MiniHolding {
  symbol: string;
  weight: number;
  pnl_pct: number;
  color: string;
}

const TOP_HOLDINGS: MiniHolding[] = [
  { symbol: "RELIANCE", weight: 22, pnl_pct: 4.2, color: "#00D4FF" },
  { symbol: "TCS", weight: 18, pnl_pct: -1.3, color: "#00E676" },
  { symbol: "HDFCBANK", weight: 15, pnl_pct: 2.8, color: "#FFB800" },
  { symbol: "INFY", weight: 12, pnl_pct: -2.1, color: "#FF3B3B" },
  { symbol: "Others", weight: 33, pnl_pct: 1.5, color: "#566176" },
];

function DonutChart({ data }: { data: MiniHolding[] }) {
  const total = data.reduce((sum, d) => sum + d.weight, 0);
  let currentAngle = -90;

  const segments = data.map((item) => {
    const angle = (item.weight / total) * 360;
    const startAngle = currentAngle;
    currentAngle += angle;
    const endAngle = currentAngle;

    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;
    const radius = 40;
    const innerRadius = 28;
    const cx = 50, cy = 50;

    const x1 = cx + radius * Math.cos(startRad);
    const y1 = cy + radius * Math.sin(startRad);
    const x2 = cx + radius * Math.cos(endRad);
    const y2 = cy + radius * Math.sin(endRad);
    const x3 = cx + innerRadius * Math.cos(endRad);
    const y3 = cy + innerRadius * Math.sin(endRad);
    const x4 = cx + innerRadius * Math.cos(startRad);
    const y4 = cy + innerRadius * Math.sin(startRad);

    const largeArc = angle > 180 ? 1 : 0;

    const d = `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} L ${x3} ${y3} A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${x4} ${y4} Z`;

    return { d, color: item.color, symbol: item.symbol };
  });

  return (
    <svg viewBox="0 0 100 100" className="h-28 w-28">
      {segments.map((seg, i) => (
        <path key={i} d={seg.d} fill={seg.color} fillOpacity={0.85} stroke="var(--nq-bg-card)" strokeWidth="1" />
      ))}
      <text x="50" y="48" textAnchor="middle" fill="var(--nq-text-primary)" fontSize="10" fontWeight="700" fontFamily="var(--font-jetbrains)">
        ₹13.4L
      </text>
      <text x="50" y="58" textAnchor="middle" fill="var(--nq-text-secondary)" fontSize="6">
        Total Value
      </text>
    </svg>
  );
}

export function PortfolioMini() {
  return (
    <Card className="flex flex-col gap-3">
      <CardHeader>
        <CardTitle>Portfolio</CardTitle>
      </CardHeader>

      <div className="flex items-center gap-4">
        <DonutChart data={TOP_HOLDINGS} />
        <div className="flex-1 space-y-1.5">
          {TOP_HOLDINGS.map((h) => (
            <div key={h.symbol} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full" style={{ backgroundColor: h.color }} />
                <span className="text-xs font-mono font-medium text-nq-text-primary">{h.symbol}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-nq-text-tertiary">{h.weight}%</span>
                <span className={cn("text-xs font-mono font-medium", getPriceColor(h.pnl_pct))}>
                  {getDirectionArrow(h.pnl_pct)} {formatPercent(h.pnl_pct)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
