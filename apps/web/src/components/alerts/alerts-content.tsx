"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus, Bell, Pause, Trash2, Edit, AlertTriangle, Brain, TrendingUp, Newspaper } from "lucide-react";
import { Card, CardHeader, CardTitle, Button, Badge } from "@neuroquant/ui";
import type { AlertType, AlertSeverity } from "@neuroquant/types";
import { alertsApi } from "@/lib/api-client";

interface ActiveAlert {
  id: string; name: string; symbol: string; type: AlertType; status: "active" | "triggered" | "paused";
  lastTriggered: string | null; timesTriggered: number;
}

interface HistoryItem {
  id: string; symbol: string; type: AlertType; severity: AlertSeverity; message: string; time: string;
}

const typeIcons: Record<AlertType, typeof Bell> = {
  price: TrendingUp, technical: TrendingUp, ml_signal: Brain,
  sentiment: Newspaper, anomaly: AlertTriangle, news: Newspaper,
};

const statusColors = { active: "bull", triggered: "warning", paused: "default" } as const;

function formatRelativeTime(input: string | null): string {
  if (!input) return "Never triggered";
  const date = new Date(input);
  const diffMs = Date.now() - date.getTime();
  if (Number.isNaN(diffMs) || diffMs < 0) return "Recently";

  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function AlertsContent() {
  const [alerts, setAlerts] = useState<ActiveAlert[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async (): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      const [definitions, events] = await Promise.all([
        alertsApi.list(),
        alertsApi.getHistory(20),
      ]);

      const mappedAlerts: ActiveAlert[] = definitions.map((item) => ({
        id: item.id,
        name: item.name,
        symbol: item.symbol ?? "NIFTY50",
        type: item.alert_type,
        status: item.is_active ? "active" : "paused",
        lastTriggered: formatRelativeTime(item.last_triggered_at),
        timesTriggered: item.times_triggered,
      }));

      const mappedHistory: HistoryItem[] = events.map((event) => ({
        id: event.id,
        symbol: event.symbol,
        type: event.alert_type,
        severity: event.severity,
        message: event.message,
        time: formatRelativeTime(event.triggered_at),
      }));

      setAlerts(mappedAlerts);
      setHistory(mappedHistory);
    } catch (fetchError) {
      const message =
        fetchError instanceof Error ? fetchError.message : "Failed to fetch alerts.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const activeCount = useMemo(
    () => alerts.filter((item) => item.status === "active").length,
    [alerts]
  );

  const createDefaultAlert = async (): Promise<void> => {
    try {
      await alertsApi.create({
        name: "NIFTY Momentum Watch",
        symbol: "NIFTY50",
        alert_type: "technical",
        conditions: { indicator: "rsi", operator: "lt", value: 35 },
        channels: ["in_app"],
        cooldown_minutes: 20,
        is_active: true,
      });
      await loadData();
    } catch (createError) {
      const message =
        createError instanceof Error ? createError.message : "Failed to create alert.";
      setError(message);
    }
  };

  const toggleAlert = async (alert: ActiveAlert): Promise<void> => {
    try {
      const nextActive = alert.status !== "active";
      await alertsApi.update(alert.id, { is_active: nextActive });
      await loadData();
    } catch (updateError) {
      const message =
        updateError instanceof Error ? updateError.message : "Failed to update alert.";
      setError(message);
    }
  };

  const removeAlert = async (alertId: string): Promise<void> => {
    try {
      await alertsApi.delete(alertId);
      await loadData();
    } catch (deleteError) {
      const message =
        deleteError instanceof Error ? deleteError.message : "Failed to delete alert.";
      setError(message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-nq-text-primary">Smart Alert Center</h1>
        <Button size="sm" onClick={() => void createDefaultAlert()} disabled={loading}>
          <Plus className="h-3.5 w-3.5" />
          New Alert
        </Button>
      </div>
      {error ? <p className="text-xs text-nq-bear">{error}</p> : null}

      <div className="grid grid-cols-12 gap-4">
        {/* Active alerts */}
        <div className="col-span-12 lg:col-span-7">
          <Card noPadding>
            <CardHeader className="px-4 pt-3">
              <CardTitle>Active Alerts</CardTitle>
              <Badge variant="accent">{loading ? "..." : `${activeCount} active`}</Badge>
            </CardHeader>
            <div className="divide-y divide-nq-border">
              {alerts.map((alert) => {
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
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => void toggleAlert(alert)}>
                        <Pause className="h-3 w-3" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7 text-nq-bear" onClick={() => void removeAlert(alert.id)}>
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                );
              })}
              {!loading && alerts.length === 0 ? (
                <div className="px-4 py-6 text-xs text-nq-text-tertiary">No alerts configured yet.</div>
              ) : null}
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
              {history.map((item) => {
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
              {!loading && history.length === 0 ? (
                <div className="px-4 py-6 text-xs text-nq-text-tertiary">No recent alert events.</div>
              ) : null}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
