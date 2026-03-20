"use client";

import { Activity, CandlestickChart, ChartNoAxesCombined, LineChart, Radar } from "lucide-react";

interface AmbientLucideBackgroundProps {
  className?: string;
}

const icons = [
  { Icon: CandlestickChart, left: "8%", top: "18%", delay: "0s", size: 18 },
  { Icon: LineChart, left: "82%", top: "22%", delay: "1.5s", size: 16 },
  { Icon: Activity, left: "16%", top: "68%", delay: "0.8s", size: 14 },
  { Icon: ChartNoAxesCombined, left: "75%", top: "72%", delay: "2.2s", size: 20 },
  { Icon: Radar, left: "46%", top: "82%", delay: "1.2s", size: 15 },
];

export function AmbientLucideBackground({ className }: AmbientLucideBackgroundProps): JSX.Element {
  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className ?? ""}`} aria-hidden="true">
      <div className="absolute inset-0 bg-[radial-gradient(860px_340px_at_8%_0%,rgba(0,212,245,0.10),transparent_55%),radial-gradient(620px_280px_at_95%_8%,rgba(0,230,118,0.08),transparent_62%)]" />
      {icons.map(({ Icon, left, top, delay, size }, index) => (
        <span
          key={`ambient-icon-${index}`}
          className="absolute animate-[floatPulse_6s_ease-in-out_infinite] text-[rgba(170,215,255,0.28)]"
          style={{ left, top, animationDelay: delay }}
        >
          <Icon size={size} strokeWidth={1.6} />
        </span>
      ))}
      <style jsx>{`
        @keyframes floatPulse {
          0% { transform: translateY(0px) scale(0.92); opacity: 0.20; }
          50% { transform: translateY(-8px) scale(1.04); opacity: 0.46; }
          100% { transform: translateY(0px) scale(0.92); opacity: 0.20; }
        }
      `}</style>
    </div>
  );
}

