"use client";

import { AlertTriangle, TrendingUp, Brain, Newspaper, Bell } from "lucide-react";
import { Card, CardHeader, CardTitle, Badge, cn } from "@neuroquant/ui";
import type { AlertSeverity, AlertType } from "@neuroquant/types";

interface FeedAlert {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  symbol: string;
  message: string;
  time: string;
}

const SAMPLE_ALERTS: FeedAlert[] = [
  { id: "1", type: "anomaly", severity: 4, symbol: "WIPRO", message: "Unusual volume spike detected — 3.2x 20-day avg", time: "2m ago" },
  { id: "2", type: "ml_signal", severity: 3, symbol: "TATAMOTORS", message: "AMSTAN model: strong BUY signal (conf: 82%)", time: "5m ago" },
  { id: "3", type: "price", severity: 2, symbol: "RELIANCE", message: "Crossed above ₹2,850 resistance level", time: "12m ago" },
  { id: "4", type: "news", severity: 3, symbol: "SBIN", message: "RBI policy: positive sentiment for banking sector", time: "18m ago" },
  { id: "5", type: "technical", severity: 2, symbol: "INFY", message: "RSI entered oversold zone (28.4)", time: "25m ago" },
];

const typeIcons: Record<AlertType, typeof Bell> = {
  price: TrendingUp,
  technical: TrendingUp,
  ml_signal: Brain,
  sentiment: Newspaper,
  anomaly: AlertTriangle,
  news: Newspaper,
};

const severityVariants: Record<AlertSeverity, "severity1" | "severity2" | "severity3" | "severity4" | "severity5"> = {
  1: "severity1",
  2: "severity2",
  3: "severity3",
  4: "severity4",
  5: "severity5",
};

export function AlertFeed() {
  return (
    <Card className="flex flex-col gap-3">
      <CardHeader>
        <CardTitle>Alerts</CardTitle>
        <Badge variant="accent">{SAMPLE_ALERTS.length} active</Badge>
      </CardHeader>

      <div className="space-y-2 max-h-64 overflow-y-auto">
        {SAMPLE_ALERTS.map((alert) => {
          const Icon = typeIcons[alert.type];
          return (
            <div
              key={alert.id}
              className="flex items-start gap-2.5 rounded-nq px-2 py-2 hover:bg-nq-bg-elevated transition-colors cursor-pointer"
            >
              <div className="mt-0.5">
                <Badge variant={severityVariants[alert.severity]} className="px-1.5 py-0">
                  <Icon className="h-3 w-3" />
                </Badge>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono text-xs font-semibold text-nq-accent">{alert.symbol}</span>
                  <span className="text-[10px] text-nq-text-tertiary">{alert.time}</span>
                </div>
                <p className="text-xs text-nq-text-secondary leading-tight mt-0.5">{alert.message}</p>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
