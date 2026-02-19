"use client";

import { useState } from "react";
import { Plus, Bell, Pause, Trash2, Edit, AlertTriangle, Brain, TrendingUp, Newspaper } from "lucide-react";
import { Card, CardHeader, CardTitle, Button, Badge, Input, cn } from "@neuroquant/ui";
import type { AlertType, AlertSeverity } from "@neuroquant/types";

interface ActiveAlert {
  id: string; name: string; symbol: string; type: AlertType; status: "active" | "triggered" | "paused";
  lastTriggered: string | null; timesTriggered: number;
}

const ACTIVE_ALERTS: ActiveAlert[] = [
  { id: "1", name: "RELIANCE breakout", symbol: "RELIANCE", type: "price", status: "active", lastTriggered: "2h ago", timesTriggered: 3 },
  { id: "2", name: "IT sector anomaly", symbol: "NIFTYIT", type: "anomaly", status: "triggered", lastTriggered: "15m ago", timesTriggered: 1 },
  { id: "3", name: "SBIN ML signal", symbol: "SBIN", type: "ml_signal", status: "active", lastTriggered: "1d ago", timesTriggered: 5 },
  { id: "4", name: "HDFCBANK RSI alert", symbol: "HDFCBANK", type: "technical", status: "paused", lastTriggered: null, timesTriggered: 0 },
  { id: "5", name: "Market sentiment shift", symbol: "NIFTY50", type: "sentiment", status: "active", lastTriggered: "4h ago", timesTriggered: 2 },
];

interface HistoryItem {
  id: string; symbol: string; type: AlertType; severity: AlertSeverity; message: string; time: string;
}

const HISTORY: HistoryItem[] = [
  { id: "h1", symbol: "WIPRO", type: "anomaly", severity: 4, message: "Volume anomaly: 3.2x average, potential institutional activity", time: "2 min ago" },
  { id: "h2", symbol: "TATAMOTORS", type: "ml_signal", severity: 3, message: "Strong BUY signal — AMSTAN confidence 82%, ensemble agrees", time: "5 min ago" },
  { id: "h3", symbol: "RELIANCE", type: "price", severity: 2, message: "Price crossed ₹2,850 resistance with high volume confirmation", time: "12 min ago" },
  { id: "h4", symbol: "NIFTYIT", type: "anomaly", severity: 4, message: "Sector correlation breakdown detected — diverging from Nifty50", time: "15 min ago" },
  { id: "h5", symbol: "SBIN", type: "news", severity: 3, message: "RBI policy decision positive for banking — sentiment score: 0.84", time: "18 min ago" },
  { id: "h6", symbol: "INFY", type: "technical", severity: 2, message: "RSI entered oversold territory at 28.4 — potential reversal zone", time: "25 min ago" },
];

const typeIcons: Record<AlertType, typeof Bell> = {
  price: TrendingUp, technical: TrendingUp, ml_signal: Brain,
  sentiment: Newspaper, anomaly: AlertTriangle, news: Newspaper,
};

const statusColors = { active: "bull", triggered: "warning", paused: "default" } as const;

export function AlertsContent() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-nq-text-primary">Smart Alert Center</h1>
        <Button size="sm"><Plus className="h-3.5 w-3.5" /> New Alert</Button>
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Active alerts */}
        <div className="col-span-12 lg:col-span-7">
          <Card noPadding>
            <CardHeader className="px-4 pt-3">
              <CardTitle>Active Alerts</CardTitle>
              <Badge variant="accent">{ACTIVE_ALERTS.filter((a) => a.status === "active").length} active</Badge>
            </CardHeader>
            <div className="divide-y divide-nq-border">
              {ACTIVE_ALERTS.map((alert) => {
                const Icon = typeIcons[alert.type];
                return (
                  <div key={alert.id} className="flex items-center gap-3 px-4 py-3 hover:bg-nq-bg-card/50 transition-colors">
                    <div className="flex h-8 w-8 items-center justify-center rounded-nq bg-nq-bg-elevated">
                      <Icon className="h-4 w-4 text-nq-text-secondary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-nq-text-primary">{alert.name}</span>
                        <Badge variant={statusColors[alert.status]}>{alert.status}</Badge>
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="font-mono text-[10px] text-nq-accent">{alert.symbol}</span>
                        <span className="text-[10px] text-nq-text-tertiary">
                          {alert.lastTriggered ? `Last: ${alert.lastTriggered}` : "Never triggered"}
                        </span>
                        <span className="text-[10px] text-nq-text-tertiary">
                          ({alert.timesTriggered}x)
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon" className="h-7 w-7"><Edit className="h-3 w-3" /></Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7"><Pause className="h-3 w-3" /></Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7 text-nq-bear"><Trash2 className="h-3 w-3" /></Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        {/* Alert history */}
        <div className="col-span-12 lg:col-span-5">
          <Card noPadding>
            <CardHeader className="px-4 pt-3">
              <CardTitle>Alert History</CardTitle>
              <Badge>Live</Badge>
            </CardHeader>
            <div className="divide-y divide-nq-border max-h-[500px] overflow-y-auto">
              {HISTORY.map((item) => {
                const Icon = typeIcons[item.type];
                const severityVar = `severity${item.severity}` as "severity1" | "severity2" | "severity3" | "severity4" | "severity5";
                return (
                  <div key={item.id} className="px-4 py-3 hover:bg-nq-bg-card/50 transition-colors">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant={severityVar} className="px-1.5 py-0"><Icon className="h-3 w-3" /></Badge>
                      <span className="font-mono text-[10px] font-semibold text-nq-accent">{item.symbol}</span>
                      <span className="text-[10px] text-nq-text-tertiary ml-auto">{item.time}</span>
                    </div>
                    <p className="text-xs text-nq-text-secondary leading-tight">{item.message}</p>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
