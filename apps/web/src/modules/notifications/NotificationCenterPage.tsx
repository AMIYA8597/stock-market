"use client";

import { useMemo } from "react";
import { BellRing, Filter, MessagesSquare } from "lucide-react";
import { Badge } from "@neuroquant/ui";
import { Button } from "@neuroquant/ui";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@neuroquant/ui";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@neuroquant/ui";
import { useNotificationsQuery } from "@/hooks/queries/useNotifications";
import { useSignalAlerts } from "@/hooks/useSignalAlerts";

export function NotificationCenterPage(): JSX.Element {
  const { data } = useNotificationsQuery();
  const { alerts } = useSignalAlerts();

  const rows = useMemo(() => {
    if (!data?.items) return [];
    return data.items.map((item) => ({
      id: item.id,
      title: item.title,
      detail: item.message,
      tone:
        item.level === "error"
          ? "sell"
          : item.level === "warning"
            ? "neutral"
            : "buy",
      time: new Date(item.created_at).toLocaleTimeString(),
    }));
  }, [data]);

  return (
    <Card className="bg-[var(--ds-surface-1)]/90">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle>Notification Center</CardTitle>
            <CardDescription>
              Unified panel for alerts, platform events, and collaboration
              updates.
            </CardDescription>
          </div>
          <Button variant="secondary" size="sm">
            <Filter className="mr-1 h-4 w-4" /> Filter
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="all">
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="alerts">Alerts</TabsTrigger>
            <TabsTrigger value="messages">Messages</TabsTrigger>
          </TabsList>
          <TabsContent value="all" className="mt-4 space-y-2">
            {rows.map((item) => (
              <div
                key={item.id}
                className="flex items-start justify-between gap-3 rounded-[var(--ds-radius-lg)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)] p-3"
              >
                <div className="flex items-start gap-2">
                  <BellRing className="mt-0.5 h-4 w-4 text-[var(--ds-color-primary-300)]" />
                  <div>
                    <p className="text-sm font-medium">{item.title}</p>
                    <p className="text-xs text-[var(--ds-text-secondary)]">
                      {item.detail}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <Badge variant={item.tone as "buy" | "sell" | "neutral"}>
                    {item.id}
                  </Badge>
                  <p className="mt-1 text-[11px] text-[var(--ds-text-muted)]">
                    {item.time}
                  </p>
                </div>
              </div>
            ))}
          </TabsContent>
          <TabsContent
            value="alerts"
            className="mt-4 space-y-2"
          >
            {alerts.length === 0 ? (
              <div className="text-sm text-[var(--ds-text-secondary)] p-2">
                No signal alerts yet.
              </div>
            ) : null}
            {alerts.map((alert, i) => (
              <div
                key={`${alert.timestamp}-${i}`}
                className="flex items-start justify-between gap-3 rounded-[var(--ds-radius-lg)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)] p-3"
              >
                <div className="flex items-start gap-2">
                  <BellRing className="mt-0.5 h-4 w-4 text-nq-accent" />
                  <div>
                    <p className="text-sm font-medium">{alert.symbol} - {alert.direction}</p>
                    <p className="text-xs text-[var(--ds-text-secondary)]">
                      {alert.message}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <Badge variant={alert.direction.includes("BUY") ? "bull" : "bear"}>
                    {alert.confidence}% Conf
                  </Badge>
                  <p className="mt-1 text-[11px] text-[var(--ds-text-muted)]">
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
          </TabsContent>
          <TabsContent value="messages" className="mt-4">
            <div className="rounded-[var(--ds-radius-lg)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)] p-5 text-sm text-[var(--ds-text-secondary)] inline-flex items-center gap-2">
              <MessagesSquare className="h-4 w-4" /> Team messages will appear
              here.
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
